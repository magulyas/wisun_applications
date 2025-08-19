#!/usr/bin/env python3
# vim: set sw=2 expandtab:

import sys
import argparse
import logging

from common_executor import CommonExecutor, ExecutionMode, ProvisionMode

if __name__ == '__main__':
  logger = logging.getLogger('provision')
  logger.setLevel(logging.DEBUG)
  ch = logging.StreamHandler()
  ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
  logger.addHandler(ch)

  parser = argparse.ArgumentParser(description='Script for performing Wi-SUN provisioning.')
  parser.add_argument('--soc', action='store', required=True, help='SoC type')
  parser.add_argument('--init_img', action='store', default=None, help='Input file for initialization data')
  parser.add_argument('--prov_img', action='store', required=True, help='Input file for provisiong application')
  parser.add_argument('--jlink_ser', action='store', default=None, help='Serial number of J-Link adapter')
  parser.add_argument('--jlink_host', action='store', default=None, help='Host name or IP address of J-Link adapter')
  parser.add_argument('--app', action='store', default=None, help='Input file for application')
  parser.add_argument('--nvm3', action='store_true', default=False, help='?')
  parser.add_argument('--certification', action='store_true', default=False, help='Certification mode')
  parser.add_argument('--cpms', action='store_true', default=False, help='CPMS mode')
  parser.add_argument('--oid', action='store', default=None, help='Product OID when CPMS mode is set')
  parser.add_argument('--config', action='store', default='openssl.conf', help='OpenSSL configuration file (default: openssl.conf)')

  args = parser.parse_args()

  executor = CommonExecutor(ExecutionMode.CLI)

  if args.cpms:
    if not args.oid:
      print(f'{parser.prog}: error: --oid is required when --cpms is set', file=sys.stderr)
      exit(1)
    else:
      logger.info("Start in cpms mode")
      executor.execute(ProvisionMode.CPMS, args)
  else:
    logger.info("Start in serca mode")
    executor.execute(ProvisionMode.CPMS, args)

  logger.info("Finished")
