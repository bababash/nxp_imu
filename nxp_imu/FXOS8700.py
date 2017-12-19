#!/usr/bin/env python
# Accel and Magnetometer
# MIT License

from __future__ import division
from __future__ import print_function
from .I2C import I2C
import struct

FXOS8700_ADDRESS = 0x1E  # 0011111
FXOS8700_ID = 0xC7  # 1100 0111

FXOS8700_REGISTER_STATUS = 0x00
FXOS8700_REGISTER_OUT_X_MSB = 0x01
FXOS8700_REGISTER_OUT_X_LSB = 0x02
FXOS8700_REGISTER_OUT_Y_MSB = 0x03
FXOS8700_REGISTER_OUT_Y_LSB = 0x04
FXOS8700_REGISTER_OUT_Z_MSB = 0x05
FXOS8700_REGISTER_OUT_Z_LSB = 0x06
FXOS8700_REGISTER_WHO_AM_I = 0x0D  # 11000111   r
FXOS8700_REGISTER_XYZ_DATA_CFG = 0x0E
FXOS8700_REGISTER_CTRL_REG1 = 0x2A  # 00000000   r/w
FXOS8700_REGISTER_CTRL_REG2 = 0x2B  # 00000000   r/w
FXOS8700_REGISTER_CTRL_REG3 = 0x2C  # 00000000   r/w
FXOS8700_REGISTER_CTRL_REG4 = 0x2D  # 00000000   r/w
FXOS8700_REGISTER_CTRL_REG5 = 0x2E  # 00000000   r/w
FXOS8700_REGISTER_MSTATUS = 0x32
FXOS8700_REGISTER_MOUT_X_MSB = 0x33
FXOS8700_REGISTER_MOUT_X_LSB = 0x34
FXOS8700_REGISTER_MOUT_Y_MSB = 0x35
FXOS8700_REGISTER_MOUT_Y_LSB = 0x36
FXOS8700_REGISTER_MOUT_Z_MSB = 0x37
FXOS8700_REGISTER_MOUT_Z_LSB = 0x38
FXOS8700_REGISTER_TEMPERATURE = 0x51
FXOS8700_REGISTER_MCTRL_REG1 = 0x5B  # 00000000   r/w
FXOS8700_REGISTER_MCTRL_REG2 = 0x5C  # 00000000   r/w
FXOS8700_REGISTER_MCTRL_REG3 = 0x5D  # 00000000   r/w

ACCEL_RANGE_2G = 0x00
ACCEL_RANGE_4G = 0x01
ACCEL_RANGE_8G = 0x02

ACCEL_MG_LSB_2G = 0.000244
ACCEL_MG_LSB_4G = 0.000488
ACCEL_MG_LSB_8G = 0.000976
MAG_UT_LSB = 0.1


# def twos_comp(val, bits):
# 	"""compute the 2's complement of int value val"""
# 	if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
# 		val = val - (1 << bits)        # compute negative value
# 	return val                         # return positive value as is


class FXOS8700(I2C):
    scale = None  # turn readings into accelerations: 2, 4, 8 G

    def __init__(self, gs=None, bus=1, verbose=False):
        """
        Args
            gs: accel range: 2, 4, or 8 G's
            bus: i2c bus to use, default is 1
            verbose: print out some info at start
        """
        I2C.__init__(self, FXOS8700_ADDRESS, bus=bus)
        if self.read8(FXOS8700_REGISTER_WHO_AM_I) != FXOS8700_ID:
            raise Exception('Error talking to FXOS8700 at', hex(FXOS8700_ADDRESS))

        # Set to standby mode (required to make changes to this register)
        self.write8(FXOS8700_REGISTER_CTRL_REG1, 0)

        # Configure the accelerometer
        # _range = None
        if gs == 2 or gs is None:
            self.write8(FXOS8700_REGISTER_XYZ_DATA_CFG, ACCEL_RANGE_2G)
            self.scale = ACCEL_MG_LSB_2G
        # _range = '2G'
        elif gs == 4:
            self.write8(FXOS8700_REGISTER_XYZ_DATA_CFG, ACCEL_RANGE_4G)
            self.scale = ACCEL_MG_LSB_4G
        # _range = '4G'
        elif gs == 8:
            self.write8(FXOS8700_REGISTER_XYZ_DATA_CFG, ACCEL_RANGE_8G)
            self.scale = ACCEL_MG_LSB_8G
        # _range = '8G'
        else:
            raise Exception('Invalide accel range: {}'.format(gs))

        # High resolution mode
        self.write8(FXOS8700_REGISTER_CTRL_REG2, 0x02)

        # Disable the magnetometer
        self.write8(FXOS8700_REGISTER_MCTRL_REG1, 0x00)

        # Device Active, Normal Read Mode, Low Noise (Restricted to 2g or 4g), 800Hz in accel only mode
        self.write8(FXOS8700_REGISTER_CTRL_REG1, 0x5)

        if verbose:
            print('=' * 40)
            print('FXOS8700')
            print('  Accelerometer:')
            print('    Addr: 0x1F')
            print('    Range: +/- {} G'.format(gs))
            print('  Magnetometer:')
            print('    Range: +/- 1200')
            print('  Temperature: {} C'.format(self.temperature()))

    def __del__(self):
        self.i2c.close()

    def temperature(self):
        """
        Return temperature in C
        Range is -128 to 127 C ... should i worry about the negative?
        """
        data = [self.read8(FXOS8700_REGISTER_TEMPERATURE)]
        # print('intermediate tmp:', data)
        # return self.twos_comp(t, 8)
        data = bytearray(data)
        return struct.unpack('b', data)[0]

    def get(self):
        # 13 bytes: status, ax,ay, az, mx, my, mz
        # status, axhi, axlo, ayhi, aylo ... mxhi, mxlo ...

        data = self.read_block(0x1, 12)  # burst read X_MSB, Y_MSB, Z_MSB

        data = bytearray(data)
        data = struct.unpack('>hhhhhh', data)

        d = data[:3]
        accel = ([(x >> 2) * self.scale for x in d])

        d = data[3:]
        mag = ([x * MAG_UT_LSB for x in d])

        return tuple(accel), tuple(mag)
