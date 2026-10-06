# src/hardware/adc.py

import spidev
from gpiozero import DigitalOutputDevice

from config import (
    SPI_BUS,
    SPI_DEVICE,
    SPI_SPEED_HZ,
    SPI_MODE,
    MCP2_CS,
    MCP3_CS,
)







class MCP3208:

    def __init__(self):

        # --------------------------------------------------
        # SPI
        # --------------------------------------------------

        self.spi = spidev.SpiDev()

        self.spi.open(
            SPI_BUS,
            SPI_DEVICE
        )

        self.spi.max_speed_hz = SPI_SPEED_HZ
        self.spi.mode = SPI_MODE

        # --------------------------------------------------
        # MANUAL CS
        #
        # MCP1 uses Raspberry Pi CE0 / GPIO8
        # MCP2 uses GPIO24
        # MCP3 uses GPIO22
        # --------------------------------------------------

        self.cs2 = DigitalOutputDevice(
            MCP2_CS,
            initial_value=True
        )

        self.cs3 = DigitalOutputDevice(
            MCP3_CS,
            initial_value=True
        )

    def read_channel(self, adc_index, channel):

        if not 0 <= adc_index < 3:
            raise ValueError(
                "Invalid ADC index"
            )

        if not 0 <= channel < 8:
            raise ValueError(
                "Invalid channel"
            )

        # MCP3208 command
        tx = [
            0x06 | ((channel & 0x04) >> 2),
            (channel & 0x03) << 6,
            0x00
        ]

        # --------------------------------------------------
        # Select ADC
        # --------------------------------------------------

        if adc_index == 0:
            # MCP1
            #
            # GPIO8 / CE0 is automatically controlled
            # by the SPI driver.
            #
            rx = self.spi.xfer2(tx)

        elif adc_index == 1:

            self.cs2.off()

            try:
                rx = self.spi.xfer2(tx)
            finally:
                self.cs2.on()

        elif adc_index == 2:

            self.cs3.off()

            try:
                rx = self.spi.xfer2(tx)
            finally:
                self.cs3.on()

        # --------------------------------------------------
        # Decode 12-bit ADC value
        # --------------------------------------------------

        value = (
            ((rx[1] & 0x0F) << 8)
            | rx[2]
        )

        return value

    def read_all_channels(self):

        values = []

        for adc in range(3):

            for channel in range(8):

                value = self.read_channel(
                    adc,
                    channel
                )

                values.append(value)

        return values

    def close(self):

        self.cs2.close()
        self.cs3.close()

        self.spi.close()