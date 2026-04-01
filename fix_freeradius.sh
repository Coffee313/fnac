#!/bin/bash

# Fix FreeRADIUS configuration for FNAC

echo "[*] Backing up current radiusd.conf..."
sudo cp /etc/freeradius/3.0/radiusd.conf /etc/freeradius/3.0/radiusd.conf.backup

echo "[*] Creating minimal FreeRADIUS configuration..."
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

listen {
	type = auth
	ipv6addr = ::
	port = 1812
	proto = udp
}

listen {
	type = acct
	ipv6addr = ::
	port = 1813
	proto = udp
}

modules {
	$INCLUDE mods-enabled/
}

server default {
	authorize {
		preprocess
		auth_log
		files
	}

	authenticate {
		Auth-Type PAP {
			pap
		}
	}

	accounting {
		detail
		unix
		exec
		attr_filter.accounting_response
	}

	session {
	}

	post-auth {
		Post-Auth-Type REJECT {
			attr_filter.access_reject
			eap
			remove_reply_message_if_eap
		}
		Post-Auth-Type Challenge {
		}
		exec
		remove_reply_message_if_eap
	}

	pre-proxy {
	}

	post-proxy {
		eap
	}
}
EOF

echo "[*] Validating FreeRADIUS configuration..."
sudo freeradius -C -d /etc/freeradius/3.0

if [ $? -eq 0 ]; then
	echo "[+] Configuration is valid!"
	echo "[*] Restarting FreeRADIUS..."
	sudo systemctl restart freeradius
	
	sleep 2
	
	if sudo systemctl is-active --quiet freeradius; then
		echo "[+] FreeRADIUS is running!"
		sudo systemctl status freeradius
	else
		echo "[-] FreeRADIUS failed to start"
		sudo systemctl status freeradius
	fi
else
	echo "[-] Configuration validation failed!"
	exit 1
fi
