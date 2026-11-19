# LuminaOS Kali Linux Security Suite profile
# Sourced by `lumina-terminal --kali` and the desktop entry.
# Kept in /etc/lumina so a single system image can enable Security mode.
export KALI_ENV=1
export PATH="/usr/local/sbin:/usr/sbin:/sbin:/usr/share/kali-menu:/opt/metasploit-framework/bin:$PATH"

if [ -n "$BASH_VERSION" ]; then
    # Kali-style prompt: kali@lumina [current dir] $
    PS1='\[\033[01;34m\](\[\033[01;31m\]kali\[\033[01;37m\]@\[\033[01;34m\]lumina\[\033[01;34m\])-[\[\033[00m\]\w\[\033[01;34m\]]\n\[\033[01;34m\]\$ \[\033[00m\]'
fi

# Print the banner once per session
if [ -t 1 ] && [ -z "$KALI_BANNER_SHOWN" ]; then
    export KALI_BANNER_SHOWN=1
    echo -e "\033[01;34m"
    echo "   ┌──────────────────────────────────────────────────┐"
    echo "   │          Kali Linux Security Suite               │"
    echo "   │              running on LuminaOS                  │"
    echo "   └──────────────────────────────────────────────────┘"
    echo -e "\033[01;32m[*] Security tools: nmap  wireshark  john  aircrack-ng  sqlmap  hydra\033[00m"
    echo -e "\033[00;36m[*] Type 'kali-tools' for a tool and package manager.\033[00m"
    echo ""
fi

# Short aliases for speed
alias nmap='nmap --privileged'
alias msf='msfconsole'
alias enum='enum4linux -a'
alias listeners='netstat -tulpn | grep LISTEN'
alias myip='curl -s ifconfig.me; echo'
