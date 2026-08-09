# twin28xx

Twin DRV8316 motor drivers controlled by an STM32G473 with an onboard MT6701 magnetic encoder for each motor. Sized to fit two iPOWER GM2804 / Cubemars GL-30 motors on the back of the PCB.

![twin28xx PCB](twinspora/image.png)

## Specs

- **MCU:** STM32G473
- **Motor drivers:** 2× DRV8316CR (Controlled via SPI)
- **Encoder:** MT6701 onboard. Optional SPI breakout for remotely-mounted motors — desolder 3× 0603 resistors to disconnect onboard sensor & use "JST" SH-1.0 6 pin header.
- **Connectivity:** CAN-FD, USB 2.0, I²C

## Power & decoupling

- 2x B2B (BK22C07-4DP/2-0.4V) for power input + CAN. In the future there will be alternate versions with screw terminal & XT-30. 
- Reverse-polarity protection on the supply input
- 2× 330 µF electrolytic bulk caps
- 12× 0805 ceramic footprints (6 per driver) for additional decoupling

## Protection

- ESD protection on every external connector

## Configuration

- 2.54mm through hole headers for CAN bus termination and I²C pull-ups

Inspired by/references:
- microspora: https://oshwlab.com/the.skuric/microspora-simplefoc-antun
- Lemon Pepper Stepper: https://github.com/VIPQualityPost/lemon-pepper-stepper
