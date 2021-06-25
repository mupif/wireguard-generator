# Wireguard generator

Generator for (incremental) Wireguard VPN configuration via JSON config files.

**Configuration file:** VPN config is stored in JSON file; the topology is always star, `net` being the central node (hub) of the VPN. Its endpoints are given by `extAddr` and `extPort`. The interface (`iface`) is used on the central node, peers have their configuration stored as `iface_peer.conf`, usable with `wg-quick`. See below for example configuration.

**Generated files** are:

* `{hubDir}/{iface}.conf` (where `hubDir` is usually `/etc/wireguard`); it contains the central node definition (including the private key), plus all peers (their public key and network addresses). When `restart` is true, `systemctl restart wg-quick@{iface}.service` is called to apply the new configuration.
* `{peerDir}/{iface}_{peer}.conf`: this file is to be installed on clients, contains the peer's private key (for authentication to the central node), central node's publick key and its endpoint to connect to. Only VPN-related traffic will be routed through the connection. *Distribute this file to the end-user securely*.
* `peerMap` is JSON for mapping public keys to user-friendly names (used by a VPN monitoring tool).

**Incremental operation**: if a peer (identified by itse friendly name) exists already in the hub config, it is entirely skipped.

## Client installation

Follow [this official guide](https://www.wireguard.com/install/) for installation of Wireguard itself.

To set up the VPN itself,

* Linux: save the client configuration file in `/etc/wireguard`, use [wg-quick](https://www.wireguard.com/quickstart/#quick-start) to bring up the interface (e.g. `sudo wg-quick up musicode_peerX.conf`).
* Windows: in the WireGuard GUI, click on "Add Tunnel" and then "Import tunnel(s) from file…"; import the `{peer}.conf` file and activate the tunnel.

### Testing the Musicode infrastructure

Ping the nameserver form the console (`cmd.exe` in windows), if Pyro5 utils are in the path:

```
$ pyro5-nsc -n 172.20.0.1 -p 10000 ping
Name server ping ok.

```

Alternatively, run `python3 -c 'import Pyro5.api; print(Pyro5.api.locate_ns(host="172.20.0.1",port=10000))'`

which should show something like the following if the server can be connected to:
```
<Pyro5.client.Proxy at 0x7fd2b3c4f100; connected IPv4; for PYRO:Pyro.NameServer@172.20.0.1:10000; owner 140542936770368>
```

## Example config

```json
{
  "iface":"musicode",
  "net":"172.16.0.1/12",
  "extAddr":"1.2.3.4",
  "extPort":"56789",
  "hubDir":"test",
  "peerDir":"test/peers",
  "restart":0,
  "peerMap":"test/peers.json",
  "peers":[
     ["peer1","172.16.0.2"],
     ["peer2","172.16.0.3"],
     ["test3","172.16.0.4"],
     ["test4","172.16.0.5"],
     ["test5","172.16.0.6"]
  ]
}
```
