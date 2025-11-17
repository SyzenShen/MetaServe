#!/usr/bin/env python

import os, re, sys
import subprocess
from argparse import ArgumentParser


def run_shell(cmd):
    """run linux shell

    Args:
        cmd (string): command
    """
    try:
        print(cmd)
        status = subprocess.call(cmd, shell=True)
    except:
        print("Couldn't run : " + cmd + ", please check it manually\n")
        sys.exit(OSError)



AP = ArgumentParser()
AP.add_argument('-o',
                '--outdir',
                dest='outdir',
                help='output dir',
                default='./')
AP.add_argument('-m',
                '--mail',
                dest='mail',
                help='releas email',
                default='mail.txt')


args = AP.parse_args()
args.mail = os.path.abspath(args.mail)
args.outdir = os.path.abspath(args.outdir)

(user, passwd, dirpath, dlink) = ('','','','')
with open(args.mail,'r') as fi:
    for line in fi:
        if '登录账号：' in line:
            user = line.strip()[5:]
        if '登录密码：' in line:
            passwd = line.strip()[5:]
        if '数据路径为：' in line:
            dirpath = line.strip()[6:]
        if '提取码：' in line:
            passwd = line.strip()[4:]
        if '下载链接：' in line:
            dlink = line.strip()[5:]

os.system("mkdir -p " + args.outdir)
os.chdir(args.outdir)

if dirpath != '':
    if dirpath[-1] == '/':
        dirpath = dirpath[:-1]
    batchDir = os.path.basename(dirpath)
    os.system(f'mkdir -p {batchDir}')
    os.chdir(batchDir)
    lndPATH = '/home/yanpc/software/linuxnd/'
    login = f'{lndPATH}lnd login -u {user} -p {passwd}'
    print(login)
    run_shell(login)

    listfile = f'{lndPATH}lnd list oss://{dirpath} > ./file.list'
    run_shell(listfile)

    files = []
    md5s = ''
    with open('file.list','r') as fi:
        for line in fi:
            cols = line.strip().split('\t')
            if cols[-1].endswith('fastq.gz') or cols[-1].endswith('fq.gz'):
                if cols[-1][0] == '/' : cols[-1] = cols[-1][1:]
                files.append(cols[-1])
            if 'md5' in cols[-1] or 'MD5' in cols[-1]:
                if cols[-1].endswith('txt'):
                    md5s = cols[-1]
    if md5s == '':
        print('not find MD5 file, download with no MD5 checking')
    else:
        print(f'found MD5 file: {md5s}')
        down = f'{lndPATH}lnd cp oss://{dirpath}{md5s} ./'
        run_shell(down)
        toSum = ''
        with open(os.path.basename(md5s),'r') as fi:
            for line in fi:
                cols = line.strip().split()
                if cols[-1] in files:
                    toSum = toSum + line
        with open(os.path.basename(md5s),'w') as fo:
            fo.write(toSum)

    for f in files:
        if os.access(f'./{f}', os.R_OK):
            print(f"already found ./{f}, skip")
        else:
            subdir = os.path.dirname(f)
            os.system(f'mkdir -p {subdir}')
            down = f'{lndPATH}lnd cp oss://{dirpath}/{f} {subdir}'
            run_shell(down)

    if not md5s == '':
        run_shell('md5sum -c ' + os.path.basename(md5s) + ' > check_md5.txt')
        with open('check_md5.txt','r') as fi:
            for line in fi:
                cols = line.strip().split(': ')
                if cols[0] in files:
                    if cols[-1] == 'OK':
                        print('%s is OK' % (cols[0]))
                    else:
                        f = cols[0]
                        subdir = os.path.dirname(f)
                        os.system(f'rm -rf {subdir}')
                        os.system(f'mkdir -p {subdir}')
                        print(f'{f} md5 checking failed, redownload...')
                        down = f'{lndPATH}lnd cp oss://{dirpath}/{f} {subdir}'
                        print(down)
                        run_shell(down)
                else:
                    print('skip file: '+cols[0])

if dlink != '':
    obsutilPATH = '/home/yanpc/software/obsutil_linux_amd64_5.7.3/'
    down = f'{obsutilPATH}obsutil share-cp {dlink} {args.outdir} -ac={passwd} -f -r -vmd5'
    run_shell(down)
