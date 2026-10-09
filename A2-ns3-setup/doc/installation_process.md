# ns-3 Installation

- [ns-3 Installation](#ns-3-installation)
  - [0 Platform Information](#0-platform-information)
  - [1 Prerequisites](#1-prerequisites)
  - [2 Installation](#2-installation)
  - [3 Configuration, Build and Testing](#3-configuration-build-and-testing)
    - [3.1 Running an Example Script](#31-running-an-example-script)
  - [4 Issues Encountered](#4-issues-encountered)


## 0 Platform Information

| Item | Value |
| :--- | :--- |
| ns-3 version | ns-3.48 |
| Operating system | Fedora Linux 44 |
| Kernel | 7.2.7-200.fc44.x86_64 (64 bit) |
| Desktop | KDE Plasma 6.7.5 (Frameworks 6.30.0, Qt 6.11.2), Wayland |
| Device | Lenovo ThinkPad X1 Carbon Gen 9 (20XXS33900) |
| CPU | Intel Core i7-1165G7 @ 2.80 GHz, 8 threads |
| Memory | 32 GiB (31.1 GiB usable) |
| GPU | Intel Iris Xe Graphics |

## 1 Prerequisites

| Purpose | Tool | Minimum version | Installed version |
| :--- | :--- | :--- | :--- |
| Download | git, or tar and bunzip2 | none | 2.55.0 |
| Compiler | g++ or clang++ | g++ >= 11.1 or clang++ >= 17 | g++ 16.2.1 |
| Configuration | python3 | >= 3.10 | 3.14.7 |
| Build system | cmake | >= 3.25 | 4.3.0 |
| Build system | make, ninja or Xcode  | none | ninja 1.13.2 |

![Version check of the ns-3 prerequisites](01_version_check_requirements.png)

## 2 Installation

Download and extract the ns-allinone release:

```
$ wget https://www.nsnam.org/releases/ns-allinone-3.48.tar.bz2
$ tar -xjf ns-allinone-3.48.tar.bz2
$ cd ns-allinone-3.48/ns-3.48/
```

I also installed Wireshark from the Fedora repositories so I can inspect the pcap traces that ns-3 simulations generate:

```
$ sudo dnf install wireshark
```

## 3 Configuration, Build and Testing

Configuration as given in the installation guide, with examples and tests enabled:

```
$ ./ns3 configure --enable-examples --enable-tests
```

![Output of the configuration step](02_first_configuration.png)

Build:

```
$ ./ns3 build
```

![Output of the first build](03_first_build.png)

Unit tests:

```
$ ./test.py
```

![Unit test output, part 1](04_unit_test_1.png)
![Unit test output, part 2](04_unit_test_2.png)


### 3.1 Running an Example Script

I ran the included traffic control example:

```
$ ./ns3 run examples/traffic-control/traffic-control-example.cc
```

![Output of the traffic control example](05_traffic_control_example.png)

The example ran without errors. ns-3 does not document expected output for this example. As an extra check, I gave the source code and the output to an AI assistant (Claude Opus 5.5), which judged the output plausible. The installation is verified mainly by the passing unit test suite.

## 4 Issues Encountered

None. Installation, configuration, build and tests all completed without errors.