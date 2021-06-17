#!/usr/bin/env python3

# Název:            fileget.py
# Předmět:          Počítačové komunikace a sítě
# Instituce:        VUT FIT
# Autor:            Pavel Bobčík
# Login:            xbobci03
# vytvořeno:        20. březen 2021
# Kompatiliblita:   Python3 a vyšší

import sys
import re
import socket

agent = "xbobci03"

# Pomocná funkce na ukončení programu s chybovým hlášením
# @param errorCode hodnota exit code
# @param errorMsg řetězec chybového hlášení
def exitCode(errorCode, errorMsg):
    print(errorMsg, file=sys.stderr)
    sys.exit(1)

# Pomocná funkce na kontrolu parametrů z příkazové řádky
def checkParam():
    if (len(sys.argv) != 5):
        exitCode(1, "E:   Chyba při spuštění. Uveden špatný počet parametrů.")
    else:
        if ((sys.argv[1] != "-n" and sys.argv[1] != "-f") or (sys.argv[3] != "-n" and sys.argv[3] != "-f")):
            exitCode(1, "E:   Chyba při spuštění. Uveden špatný tvar parametrů.")
        elif ((sys.argv[1] == "-n" and sys.argv[3] != "-f") or (sys.argv[1] == "-f" and sys.argv[3] != "-n")):
            exitCode(1, "E:   Chyba při spuštění. Uveden špatný tvar parametrů.")
        elif (((sys.argv[1] == "-n") and (not (re.search("^([0-9]{1,3}.){3}[0-9]{1,3}:[0-9]+$", sys.argv[2]))))
              or ((sys.argv[3] == "-n") and (not (re.search("^([0-9]{1,3}.){3}[0-9]{1,3}:[0-9]{1,5}$", sys.argv[4]))))):
            exitCode(1, "E:   Chyba při spuštění. Uveden špatný formát parametru IP adresy '-n'.")
        elif (((sys.argv[1] == "-f") and (not (re.search("^fsp:\/\/[a-zA-Z0-9._-]+\/(\/|[^ \/]*|(\/\*)?)+$", sys.argv[2]))))
              or ((sys.argv[3] == "-f") and (not (re.search("^fsp:\/\/[a-zA-Z0-9._-]+\/(\/|[^ \/]*|(\/\*)?)+$", sys.argv[4]))))):
            exitCode(1, "E:   Chyba při spuštění. Uveden špatný formát parametru SURL '-f'.")

# Funkce na získání IP adresy a portu nameserver z argumentu a jejich kontrolu rozsahu
# @return IP adresa, port
def getNameserverIpAndPort():
    nameserver = sys.argv[2] if sys.argv[1] == "-n" else sys.argv[4]
    ip = nameserver.split(":")
    nameserverSplit = ip[0].split(".")
    for part in nameserverSplit:
        if (int(part) > 255):
            exitCode(1, "E:   Chybný formát IP adresy. Uvedená IP adresa překročila rozsah 0-255.")
    if (int(ip[1]) > 65535):
            exitCode(1, "E:   Chybný formát portu. Uvedený port překročil rozsah 0-65535.")
    return ip[0], int(ip[1])

# Funkce na získání protokolu a úpravu hodnoty surl
# @return protokol, surl
def getProtocolAndUpdateSurl():
    protocol = sys.argv[2].split("://")[0] if sys.argv[1] == "-f" else sys.argv[4].split("://")[0]
    surl = sys.argv[2].split("://")[1] if sys.argv[1] == "-f" else sys.argv[4].split("://")[1]
    return protocol, surl

# Funkce na získání jména serveru ze surl
# @param surl surl obsahující jméno serveru a cestu
# @return jméno serveru
def getServerName(surl):
    if (re.search("//", surl)):
        exitCode(1, "E:   Chybný formát názvu serveru nebo cesty.")
    return surl.split("/")[0]

# Funkce na zjištění a kontrolu cesty a souboru
# @param surl surl obsahující jméno serveru a cestu
# @return jméno cesty, jméno souboru 
def getPathAndFileName(surl):
    path = ""
    splited = surl.split("/")
    for i in range(1, len(splited)):
        path += "/" + splited[i] if (i != 1) else splited[i]
    if (path == ""):
        exitCode(1, "E:   Chybějící cesta nebo soubor.")
    file = splited[len(splited)-1]
    if (file == ""):
        exitCode(1, "E:   Chybějící soubor.")
    return path, file

# Funkce zprostředkující protokol NSP
# @nameserverIP IP adresa nameserver
# @nameserverPort port nameserver
# @serverName jméno serveru, jehož IP chceme nalézt
# @return nalezená IP a port
def getIPFromNameByNSP(nameserverIP, nameserverPort, serverName):
    msgToNSP = "WHEREIS " + serverName
    bytesMsgToNSP = str.encode(msgToNSP)
    bufferSize = 1024

    udpSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    for i in range(0,4):
        try:
            udpSocket.connect((nameserverIP, nameserverPort))
            udpSocket.sendall(bytesMsgToNSP)
            udpSocket.settimeout(30)
            msgFromNSP = udpSocket.recv(bufferSize).decode("utf-8")
            break
        except ConnectionRefusedError:
            exitCode(1, "E:   Chyba při navázání komunikace s jmenným serverem "+ nameserverIP +":"+ str(nameserverPort) +".")
        except socket.timeout:
            if (i < 3):
                print("W:   Pokus o navázání spojení s "+ nameserverIP +":"+ str(nameserverPort) +" selhal. ["+str(i+1)+"/4]")
                continue
            else:
                print("W:   Pokus o navázání spojení s "+ nameserverIP +":"+ str(nameserverPort) +" selhal. [4/4]")
                exitCode(1, "E:   Nezdařilo se navázat spojení s jmenným serverem.")

    udpSocket.close()

    if (re.search("err not found", msgFromNSP, re.IGNORECASE)):
        exitCode(1, "E:   Server s jménem '"+ serverName +"' nebyl nalezen.")
    elif (re.search("err syntax", msgFromNSP, re.IGNORECASE)):
        exitCode(1, "E:   Chybně sestavený NSP dotaz.")
    
    msgFromNSP = re.sub("OK[\s]*", "", msgFromNSP)
    ipAndPort = msgFromNSP.split(":")
    return ipAndPort[0], int(ipAndPort[1])

# Funkce vykonávající FSP protokol
# @path cesta
# @serverName jméno serveru, na který se připojujeme
# @agent vut login
# @serverIP IP adresa serveru, na který se připojujeme
# @serverPort port serveru, na který se připojujeme
# @fileName soubor, který cheme stáhnout
def connectToServerAndGetFile(path, serverName, agent, serverIP, serverPort, fileName):
    msgToFSP = "GET " + path + " FSP/1.0\r\nHostname: " + serverName + "\r\nAgent: " + agent + "\r\n\r\n"
    byteMsgToFSP = str.encode(msgToFSP)
    bufferSize = 1024

    tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try: 
        tcpSocket.connect((serverIP, serverPort))
        tcpSocket.sendall(byteMsgToFSP)
    except ConnectionRefusedError:
        exitCode(1, "E:   Chyba při navázání komunikace se serverem "+ serverIP +":"+ str(serverPort) +".")

    headerRecv = False
    length = 0
    downloadBytes = 0
    file = None
    while (1):
        try:
            data = tcpSocket.recv(bufferSize)
            if (headerRecv == False):
                headerRecv, length, file = checkHeader(data, fileName, path)
                downloadBytes += len(data)
                continue

            downloadBytes += len(data)
        except ConnectionRefusedError:
            exitCode(1, "E:   Chyba při navázání komunikace se serverem "+ serverIP +":"+ str(serverPort) +".")
            
        if (not data):
            break
        
        try:
            file.write(data)
        except IOError:
            exitCode(1, "E:   Nastala chyba při práci se souborem.")

    try:
        file.close()
    except IOError:
        exitCode(1, "E:   Nastala chyba při uzavírání souboru.")

    if (downloadBytes < length):
        exitCode(1, "E:   Došlo k chybě při stahování ze serveru. Data nejsou kompletní.")

    tcpSocket.close()

# Pomocná funkce na kontrolu hlavičky
# @param data obdržená data ze serveru
# @param file soubor, do kterého bude ukládat zprávu
# @param path cesta k souboru, kam bude ukládat
# @return boolean hodnota, zdali byla nalezena hlavička, délku zprávy, otevřený soubor
def checkHeader(data, fileName, path):
    if (data == ""):
        return False, 0

    if (re.search(b"^fsp/1.0[\s]*not[\s]*found", data, flags=re.IGNORECASE)):
        exitCode(1, "E:   Hledaný soubor '" + path + "' nebyl nalezen.")
    elif (re.search(b"^fsp/1.0[\s]server[\s]*error", data, flags=re.IGNORECASE)):
        exitCode(1, "E:   Při komunikaci se server došlo k chybě.")
    elif (re.search(b"^fsp/1.0[\s]bad[\s]*request", data, flags=re.IGNORECASE)):
        exitCode(1, "E:   Server nerozumí požadavku.")
    
    lengthArr = re.findall(b"length:[\s]*[0-9]+", data, re.IGNORECASE)
    length = lengthArr[0].decode("utf-8").split(":")[1]
    
    data = re.sub(b"fsp/1.0[\s]*success\r\n", b"", data, flags=re.IGNORECASE)
    data = re.sub(b"length:[\s]*[0-9]*\r\n", b"", data, flags=re.IGNORECASE)
    data = re.sub(b"^\r\n", b"", data, flags=re.IGNORECASE)

    try:
        file = open(fileName, "wb")
    except IOError:
        exitCode(1, "E:   Nastala chyba při vytváření/otevření souboru.")

    if(data):
        try:
            file.write(data)
        except IOError:
            exitCode(1, "E:   Nastala chyba při práci se souborem.")
        
    
    return True, int(length), file

# Funkce zprostředkovávající hromadné stažení
# @path cesta
# @surl surl obsahující název serveru a cestu k souboru
# @fileName soubor, který cheme stáhnout
# @serverName jméno serveru, na který se připojujeme
# @agent vut login
# @serverIP IP adresa serveru, na který se připojujeme
# @serverPort port serveru, na který se připojujeme

def downloadALl(path, surl, fileName, serverName, agent, serverIP, serverPort):
    path = path.replace("*", "index")
    surl = surl.replace("*", "index")
    fileName = "index"
    connectToServerAndGetFile(path, serverName, agent, serverIP, serverPort, fileName)
    try:
        file = open(fileName, "r")
    except IOError:
        exitCode(1, "E:   Nastala chyba při vytváření/otevření souboru.")
    for indexFilneName in file:
        if(re.search("^\n$", indexFilneName)):
            continue
        indexFilneName = re.sub("\n", "", indexFilneName)
        path = indexFilneName
        surl = serverName+"\\"+path
        indexFilneNameSplited = indexFilneName.split("/")
        indexFilneName = indexFilneNameSplited[len(indexFilneNameSplited)-1]
        connectToServerAndGetFile(path, serverName, agent, serverIP, serverPort, indexFilneName)


###############################
#   Volání pomocných funkcí   #
###############################

checkParam()
nameserverIP, nameserverPort = getNameserverIpAndPort()
protocol, surl = getProtocolAndUpdateSurl()
serverName = getServerName(surl)
path, fileName = getPathAndFileName(surl)
serverIP, serverPort = getIPFromNameByNSP(nameserverIP, nameserverPort, serverName)
if(fileName == "*"):
    downloadALl(path, surl, fileName, serverName, agent, serverIP, serverPort)
else:
    connectToServerAndGetFile(path, serverName, agent, serverIP, serverPort, fileName)


