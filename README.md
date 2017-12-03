# debian-installer (d-i) as a service

## Usage

### Debian

 * Download an official Debian [netinst](https://www.debian.org/devel/debian-installer/) image or set up dhcp&amp;tftp to use netboot.tar.gz for PXE.
 * Visit [the demo site](https://sylee.org/d-i/), edit, and save your preseed.cfg and late\_command script.
 * Boot from the netinst image you just downloaded or boot into PXE you just set up with the following kernel parameters.

`auto=true priority=critical url=sylee.org`

  * Check [B.2. Using preseeding - B.2.3. Auto mode](https://www.debian.org/releases/stable/amd64/apbs02.html.en#preseed-auto) to see how Debian stable works.

### Ubuntu

 * Download an official Ubuntu [netboot](http://cdimage.ubuntu.com/netboot/) image or set up dhcp&amp;tftp to use netboot.tar.gz for PXE.
 * Visit [the demo site](https://sylee.org/d-i/?share=00000000), edit, and save your preseed.cfg and late\_command script.
 * Boot from the netboot image you just downloaded or boot into PXE you just set up with the following kernel parameters.

`auto=true priority=critical url=sylee.org`

  * Check [B.2. Using preseeding - B.2.3. Auto mode](https://help.ubuntu.com/lts/installation-guide/amd64/apbs02.html#preseed-auto) to see how Ubuntu LTS works.

## Setup the service

`pip install flask distro-info`

`FLASK_DEBUG=1 FLASK_APP=service.py flask run`
