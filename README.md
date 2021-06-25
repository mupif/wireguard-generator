# wireguard-generator
Generator for (incremental) Wireguard VPN configuration via JSON config files.

VPN config is stored in JSON file; the topology is always star, with `net` being the central node of the VPN. Its endpoints are given by `extAddr` and `extPort`. The interface (`iface`) is used on the central node, peers have their configuration stored as `iface_peer.conf`, usable with `wg-quick`.

Files generated as `{hubDir}/{iface}.conf` (where `hubDir` is usually `/etc/wireguard`) and `{peerDir}/{iface}_{peer}.conf` (for installation on clients). `peerMap` is JSON for mapping public keys to user-friendly names (used by a VPN monitoring tool). When `restart` is true, `sudo systemctl restart wg-quick@{iface}.service` is called at the end.


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
