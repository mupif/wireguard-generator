import pyzipper, secrets, glob, string, sys, re, argparse
parser=argparse.ArgumentParser()
parser.add_argument('--peer-prefix',required=True,help='Prefix of *.conf files to zip')
parser.add_argument('--pwds',required=True,help='Zip passwords text file')
parser.add_argument('--zip-prefix',default='peers_{vpn}',help='Template for output')
parser.add_argument('--vpn',default='',help='Name of the VPN; if empty, deduced from conf files prefix')
args=parser.parse_args()
if not args.vpn: args.vpn=args.peer_prefix.split('/')[-1]

alphabet=string.ascii_letters+string.digits
with open(args.pwds,'w') as pwds:
    pp=glob.glob(f'{args.peer_prefix}_*.conf')
    partners=set([re.match(f'{args.peer_prefix}_([a-zA-Z]+)[0-9]+\.conf',p).group(1) for p in pp])
    print(f'Partners in {args.vpn} ({args.peer_prefix}) are: {", ".join(partners)}')
    for partner in partners:
        pwd=''.join(secrets.choice(alphabet) for i in range(20))
        confs=glob.glob(f'{args.peer_prefix}_{partner}*.conf')
        if not confs: raise ValueError('No configuration files for parner {partner}?')
        pwds.write(f'{partner} {pwd}\n')
        with pyzipper.AESZipFile(args.zip_prefix.format(vpn=args.vpn)+f'_{partner}.zip','w',compression=pyzipper.ZIP_LZMA,encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(bytes(pwd,encoding='ascii'))
            for conf in confs: zf.write(conf,arcname=conf.split('/')[-1])

