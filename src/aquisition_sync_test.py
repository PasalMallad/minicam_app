from acquisition.scanner import MiniCamScanner
from hardware.adc import MCP3208
from hardware.camera import Camera   

adc = MCP3208()
camera = Camera()
scanner = MiniCamScanner(adc, camera)

try:
    for _ in range(10):
        print(scanner.measure_average())
finally:
    scanner.adc.close()