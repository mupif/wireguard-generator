import wgconfig
import wgconfig.wgexec as wgexec
import argparse
import os.path
import json
import pandas as pd
import subprocess
import qlogging
log=qlogging.get_logger(level='info')

import pydantic

import ipaddress
import typing
import pathlib

class WgOpts(pydantic.BaseModel):
    class Config:
        validate_all=True
    iface: str
    addr: ipaddress.IPv4Interface='172.16.0.1/12'
    extAddr: ipaddress.IPv4Address='1.2.3.4'
    extPort: int=56789
    hubDir: pathlib.Path='/etc/wireguard/'
    peerDir: pathlib.Path='./peers'
    restart: bool=True
    iptables: bool=False
    keepalive: int=0
    peerMap: pathlib.Path='./peers.json'
    peers: typing.List[typing.Tuple[str,str]]=[]

parser=argparse.ArgumentParser()
parser.add_argument('-n','--dry-run',action='store_true',help="Do not write anything, only pretend.")
parser.add_argument('-c','--config',type=str,default='easier-wg-quick.json',help='JSON configuration file to read')
parser.add_argument('--keep-intact',action='store_true',help="Preserve existing peer configs intact (not even writing new options; debugging only)")
parser.add_argument('-v','--verbose',action='store_true',help='Show debugging messages')
cOpts=parser.parse_args()
if cOpts.verbose: log=qlogging.get_logger(level='debug')
dryRun=cOpts.dry_run
opts=WgOpts.parse_file(cOpts.config)

if not opts.addr.ip.is_private: raise RuntimeError('Hub IP {opts.addr.ip} is not a private IP address.')

def ensureDir(p,role):
    if not p.exists():
        log.info(f'Creating new directory ({role}): {p}')
        os.makedirs(str(p))

ensureDir(opts.hubDir,role='hubDir')
ensureDir(opts.peerDir,role='peerDir')

ifacecfg=f'{opts.hubDir}/{opts.iface}.conf'
wc=wgconfig.WGConfig(ifacecfg)
if not os.path.exists(ifacecfg):
    log.info(f'Creating new hub config: {ifacecfg}.')
    wc.initialize_file()
    wc.add_attr(None,'Address',opts.addr)
    wc.add_attr(None,'ListenPort',opts.extPort)
    wc.add_attr(None,'PrivateKey',wgexec.generate_privatekey())
    if opts.iptables: wc.add_attr(None,'PostUp',f'iptables -A INPUT -p udp --dport {opts.extPort} -j ACCEPT')
    if not dryRun: wc.write_file()
    else: log.info(f'--dry-run: not writing {ifacecfg}')
else: log.info(f'Using existing hub config: {ifacecfg}.')

def reread(cfg):
    'Reload config and load friendly_json comment'
    if not (dryRun and not os.path.exists(ifacecfg)): cfg.read_file()
    else: log.info(f'--dry-run: non-existent {ifacecfg} not re-read')
    for peer,cfg in cfg.peers.items():
        friendly=[json.loads(l.split('=',1)[1]) for l in cfg['_rawdata'] if l.startswith('# friendly_json =')]
        if len(friendly)!=1: raise ValueError(f'Multiple or no friendly_json comments in peer {peer}.')
        cfg['friendly']=friendly[0]

def peers_df(cfg):
    'Return peer configuration as pandas dataframe'
    if not cfg.peers: return None
    return pd.DataFrame.from_dict({'friendly name':[d['friendly']['name'] for d in cfg.peers.values()],'IP address':[d['AllowedIPs'] for d in cfg.peers.values()],'public key':list(cfg.peers.keys())})

reread(wc)
log.info('Current peer list:\n'+str(peers_df(wc)))

if opts.peers:
    for name,ip in opts.peers:
        if ipaddress.ip_address(ip) not in opts.addr.network: raise RuntimeError('Peer {name} IP {ip} is not hub {opts.addr} network.')
        peerCfg=f'{opts.peerDir}/{opts.iface}_{name}.conf'
        log.debug(peerCfg)
        extant=bool(pp:=[peer for peer,data in wc.peers.items() if data['friendly']['name']==name])
        if extant and cOpts.keep_intact:
            log.warning(f'{name}: not touching existing in hub config as per --keep-intact (pubkey: {pp[0]}).')
            continue
        if extant:
            log.info(f'{name}: update existing in hub config')
            if not os.path.exists(peerCfg): raise RuntimeError(f'Unable to find existing config file for peer {name} in {peerCfg}, cannot update (delete the peer from hub config by hand).')
            cpeer0=wgconfig.WGConfig(peerCfg)
            cpeer0.read_file()
            pub=pp[0]
            priv=cpeer0.interface['PrivateKey']
            preshared=wc.peers[pub]['PresharedKey']
            wc.del_peer(pub)
        else:
            log.info('{name}: creating new peer')
            priv,pub=wgexec.generate_keypair()
            preshared=wgexec.generate_presharedkey()
        if len(f'{opts.iface}_{name}')>15: raise ValueError(f'{opts.iface}_{name} is longer than 15 characters (maximum network interface name in Linux).')
        peerIpMask=f'{ip}/{opts.addr.network.prefixlen}'
        # check for IP addresses already in use
        if xx:=[data['friendly']['name'] for peer,data in wc.peers.items() if data['AllowedIPs']==peerIpMask]:
            raise ValueError('IP address {peerIpMask} already used by other peers: {", ".join(xx)}')
        # special comment to store extra data
        # https://github.com/MindFlavor/prometheus_wireguard_exporter/issues/54
        comment='# friendly_json = {"name":"%s"}'%name

        log.info(f'{name}: {peerIpMask} {pub}')

        # add to the central node
        wc.add_peer(pub)
        wc.add_attr(pub,'PresharedKey',preshared,comment)
        wc.add_attr(pub,'AllowedIPs',ip+'/32')
        if not dryRun: wc.write_file()
        else: log.info(f'--dry-run: not writing {ifacecfg}')
        reread(wc) # pickup any changes

        # create peer config file
        cpeer=wgconfig.WGConfig(peerCfg)
        cpeer.initialize_file(comment)
        cpeer.add_attr(None,'Address',peerIpMask)
        cpeer.add_attr(None,'PrivateKey',priv)
        wcpub=wgexec.get_publickey(wc.interface['PrivateKey'])
        cpeer.add_peer(wcpub)
        cpeer.add_attr(wcpub,'PresharedKey',preshared)
        cpeer.add_attr(wcpub,'AllowedIPs',opts.addr.network)
        cpeer.add_attr(wcpub,'Endpoint',f'{opts.extAddr}:{wc.interface["ListenPort"]}')
        if opts.keepalive>0: cpeer.add_attr(wcpub,'PersistentKeepalive',opts.keepalive)
        if not dryRun: cpeer.write_file()
        else: log.info(f'--dry-run: not writing {peerCfg}')

    reread(wc)
    log.info('New peer list:\n'+str(peers_df(wc)))

    # TODO: permissions on config files

    if opts.peerMap:
        log.info(f'Writing peer map to {opts.peerMap}')
        reread(wc)
        if not dryRun: open(opts.peerMap,'w').write(json.dumps(dict([(pubkey,data['friendly']['name']) for pubkey,data in wc.peers.items()])))
        else: log.info(f'--dry-run: not writing {opts.peerMap}')
        

    if opts.restart:
        cmd=['systemctl','restart',f'wg-quick@{opts.iface}.service']
        log.info(f'Running {" ".join(cmd)}')
        if not dryRun: subprocess.run(cmd)
