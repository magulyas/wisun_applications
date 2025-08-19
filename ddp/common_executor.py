import enum
import os
import sys
import threading

import wisun.common
import wisun.command
import wisun.response
import ddp.command
import ddp.response
import ddp.commander
from ddp.rtt import SerialWire
import SigningServer
import os

class ExecutionMode(enum.Enum):
    CLI = 1
    WEB_SERVICE = 2

class ProvisionMode(enum.Enum):
    CPMS = 1
    SERCA = 2

class CommonExecutor:
    def __init__(self, mode:ExecutionMode):
        self._mode = mode

        # TODO # logger init
        self.lock = threading.Lock()

    @property
    def mode(self):
        return self._mode

    def execute(self, prov_mode : ProvisionMode, *args, **kwargs):
        with self.lock:
            if(prov_mode == ProvisionMode.CPMS):
                return self.__cpms(*args, **kwargs)
            elif(prov_mode == ProvisionMode.SERCA):
                return self.__serca(*args, **kwargs)

    def __cpms(self, args):
        try:
            soc = wisun.common.socs[args.soc]
        except KeyError:
            print(f'Error: {args.soc} is not a supported SoC type', file=sys.stderr)
            exit(1)

        with open(args.prov_img, 'rb') as f:
            provisioning_app = f.read()

        # Connect to the device
        # logger.info("Opening SerialWire connection to the device")
        jlink_xml = os.path.join(os.path.dirname(__file__), "jlink/JLinkDevices.xml")
        sw = SerialWire(soc['device'], args.jlink_ser, args.jlink_host, jlink_xml)
        sw.connect()
        sw.reset_and_halt()
        # logger.info("Connection opened")

        try:
            # Retrieve device MAC
            # logger.info("Retrieving device serial number")
            sn = sw.get_mac_address()
            # logger.info("Device serial number: %s", sn)

            # Inject and run provisioning application
            # logger.info("Injecting provisioning application")
            ram_addr = soc['ramstartaddress']
            sw.run_application(ram_addr, provisioning_app)
            sw.rtt_start()
            # logger.info("Provisioning application running")

            # Initialize NVM
            # logger.info("Initializing NVM")
            tx = ddp.command.InitializeNvm(soc['nvm3inststartaddress'], soc['nvm3instsize'])
            sw.rtt_send(tx)
            rx = sw.rtt_receive()
            resp = ddp.response.InitializeNvm(rx)
            assert resp.status == 0, f"Failure during NVM initialization ({resp.status})"
            # logger.info("NVM initialized")

            # Generate Wi-SUN key-pair
            # logger.info("Generating Wi-SUN key pair on the device")
            tx = wisun.command.GenerateKeyPair(0x100)
            sw.rtt_send(tx)
            rx = sw.rtt_receive()
            resp = wisun.response.GenerateKeyPair(rx)
            assert resp.status in (0, 19), f"Failure during Wi-SUN key pair generation ({resp.status})"
            if resp.status == 19:
                # logger.warning("Wi-SUN key pair already exists")
                pass
            else:
                # logger.info("Wi-SUN key pair generated")
                pass

            # Generate Wi-SUN CSR
            # logger.info("Generating Wi-SUN CSR on the device")
            tx = wisun.command.GenerateCsr(0x100)
            sw.rtt_send(tx)
            rx = sw.rtt_receive()
            resp = wisun.response.GenerateCsr(rx)
            assert resp.status == 0, f"Failure during Wi-SUN CSR generation ({resp.status})"
            # logger.info("Wi-SUN CSR generated")

            # Generate Wi-SUN device certificate
            # logger.info("Generating Wi-SUN device certificate")
            device, batch, root = SigningServer.GetCerts(resp.csr, sn, args.config)
            # logger.info("Wi-SUN device certificate generated")

            # Write Wi-SUN device certificate into NVM
            # logger.info("Saving Wi-SUN device certificate into NVM")
            tx = ddp.command.WriteNvm(0x100, device)
            sw.rtt_send(tx)
            rx = sw.rtt_receive()
            resp_device = ddp.response.WriteNvm(rx)
            assert resp_device.status == 0, f"Failure saving Wi-SUN device certificate into NVM ({resp_device.status})"
            # logger.info("Wi-SUN device certificate saved")

            # Write Wi-SUN batch certificate into NVM
            # logger.info("Saving Wi-SUN batch certificate into NVM")
            tx = ddp.command.WriteNvm(0x101, batch)
            sw.rtt_send(tx)
            rx = sw.rtt_receive()
            resp_batch = ddp.response.WriteNvm(rx)
            assert resp_batch.status == 0, f"Failure saving Wi-SUN batch certificate into NVM ({resp_batch.status})"
            # logger.info("Wi-SUN batch certificate saved")

            # Write Wi-SUN root certificate into NVM
            # logger.info("Saving Wi-SUN root certificate into NVM")
            tx = ddp.command.WriteNvm(0x102, root)
            sw.rtt_send(tx)
            rx = sw.rtt_receive()
            resp_root = ddp.response.WriteNvm(rx)
            assert resp_root.status == 0, f"Failure saving Wi-SUN root certificate into NVM ({resp_root.status})"
            # logger.info("Wi-SUN root certificate saved")
            
            return {
                'success': True,
                'device_serial': sn,
                'certificates': ['device', 'batch', 'root']
            }
            
        finally:
            sw.rtt_stop()
            sw.reset()
            sw.close()

    def __serca(self, args):
        # Implementation for SERC-A mode
        pass
