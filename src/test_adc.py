
from hardware.adc import MCP3208

adc = MCP3208()


try:
   
    values = adc.read_all_channels()

    for i, value in enumerate(values):
        print(f"D{i}: {value}")

except Exception as e:
    print(f"ADC forced to close: {e}")
    adc.close()

finally:
    adc.close()