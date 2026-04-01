#!/bin/bash

# Fix FreeRADIUS configuration for FNAC - Version 2
# Simpler config without module dependencies

echo "[*] Backing up current radiusd.conf..."
sudo cp /etc/freeradius/3.0/radiusd.conf /etc/freeradius/3.0/radiusd.conf.backup.v2

echo "[*] Creating simplified FreeRADIUS configuration..."
sudo tee /etc/freeradius/3.0/radiusd.conf > /dev/null << 'EOF'
prefix = /usr
exec_prefix = /usr
sysconfdir = /etc
localstatedir = /var
sbindir = /usr/sbin
logdir = /var/log/freeradius
raddbdir = /etc/freeradius/3.0
radacctdir = /var/log/freeradius/radacct

name = radiusd

security {
	max_attributes = 200
	reject_delay = 1
	status_server = yes
}

log {
	destination = files
	file = ${logdir}/radius.log
	syslog_facility = daemon
	stripped_names = no
	auth = no
	auth_badpass = no
	auth_goodpass = no
}

checkrad = /usr/sbin/checkrad

listen {
	type = auth
	ipaddr = *
	port = 1812
	proto = udp
}

listen {
	type = acct
	ipaddr = *
	port = 1813
	proto = udp
}

modules {
	$INCLUDE mods-enabled/
}

server default {
	authorize {
		files
	}

	authenticate {
	}

	accounting {
	}

	session {
	}

	post-auth {
	}

	pre-proxy {
	}

	post-proxy {
	}
}
EOF

echo "[*] Validating FreeRADIUS configuration..."
sudo freeradius -C -d /etc/freeradius/3.0 2>&1

if [ $? -eq 0 ]; then
	echo "[+] Configuration is valid!"
	echo "[*] Restarting FreeRADIUS..."
	sudo systemctl restart freeradius
	
	sleep 2
	
	if sudo systemctl is-active --quiet freeradius; then
		echo "[+] FreeRADIUS is running!"
		sudo systemctl status freeradius
		echo ""
		echo "[+] Checking if listening on port 1812..."
		sudo netstat -tulpn | grep 1812
	else
		echo "[-] FreeRADIUS failed to start"
		sudo systemctl status freeradius
		echo ""
		echo "[*] Checking logs..."
		sudo tail -20 /var/log/freeradius/radius.log
	fi
else
	echo "[-] Configuration validation failed!"
	exit 1
fi
