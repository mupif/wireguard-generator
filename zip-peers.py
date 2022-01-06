import pyzipper, secrets, glob, string, sys, re, argparse, qlogging, os
log=qlogging.get_logger(level='info')

parser=argparse.ArgumentParser()
parser.add_argument('--peer-prefix',required=True,help='Prefix of *.conf files to zip')
parser.add_argument('--pwds',required=True,help='Zip passwords text file')
parser.add_argument('--zip-prefix',default='peers_{vpn}',help='Template for output')
parser.add_argument('--vpn',default='',help='Name of the VPN; if empty, deduced from conf files prefix')
args=parser.parse_args()
if not args.vpn: args.vpn=args.peer_prefix.split('/')[-1]

pwds0={}
if os.path.exists(args.pwds):
    log.info(f'Re-using existing passwords in {args.pwds}')
    pwds0=dict([(ll[0],ll[1]) for l in open(args.pwds,'r') if len(ll:=(l.split()))==2])
    log.info(f'Existing passwords: '+','.join(pwds0.keys()))

alphabet=string.ascii_letters+string.digits
with open(args.pwds,'w') as pwds:
    pp=glob.glob(f'{args.peer_prefix}_*.conf')
    partners=set([re.match(f'{args.peer_prefix}_([a-zA-Z]+)[0-9]+\.conf',p).group(1) for p in pp])
    log.info(f'Partners in {args.vpn} ({args.peer_prefix}) are: {", ".join(partners)}')
    for partner in partners:
        pwd=pwds0.get(partner,''.join(secrets.choice(alphabet) for i in range(20)))
        confs=glob.glob(f'{args.peer_prefix}_{partner}*.conf')
        if not confs: raise ValueError('No configuration files for parner {partner}?')
        pwds.write(f'{partner} {pwd}\n')
        zipFile=args.zip_prefix.format(vpn=args.vpn)+f'_{partner}.zip'
        log.info(f'Writing to {zipFile}:')
        with pyzipper.AESZipFile(zipFile,'w',compression=pyzipper.ZIP_LZMA,encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(bytes(pwd,encoding='ascii'))
            for conf in confs:
                log.info(f'   {conf}')
                zf.write(conf,arcname=conf.split('/')[-1])

