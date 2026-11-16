# Besplatan server na Oracle Cloudu

Oracle *Always Free* daje ARM server s 4 jezgre i 24 GB RAM-a, besplatno i bez isteka. To je dovoljno i za dugi video.

## 1. Račun

1. Otvori račun na **oracle.com/cloud/free**.
2. Kao *Home Region* odaberi **Germany Central (Frankfurt)**. Kasnije se ne može promijeniti.
3. Traži karticu samo za provjeru. Dok koristiš *Always Free* resurse, ništa se ne naplaćuje.

> Savjet: nakon nekoliko dana račun nadogradi na **Pay As You Go**. I dalje plaćaš 0 € dok si unutar besplatnih granica,
> ali Oracle tada ne gasi servere koji malo rade (besplatnim računima to radi nakon 7 dana slabog korištenja).

## 2. Server

1. *Compute → Instances → Create instance*
2. **Image:** Canonical Ubuntu 24.04
3. **Shape:** *Change shape → Ampere → VM.Standard.A1.Flex* → **4 OCPU, 24 GB** (piše *Always Free eligible*)
   - ako javi *Out of capacity*, probaj 2 OCPU / 12 GB ili ponovno za sat-dva
4. **Boot volume:** 100 GB (besplatno je do 200 GB)
5. **SSH keys:** *Generate a key pair* → **Save private key** (bez te datoteke ne možeš ući na server)
6. *Create*. Kad zasvijetli zeleno, zapiši **Public IP address**.

## 3. Otvori portove 80 i 443

1. Na stranici servera: *Subnet* → *Security Lists* → *Default Security List* → **Add Ingress Rules**
   - Source CIDR `0.0.0.0/0`, IP Protocol TCP, Destination Port Range **80,443**
2. Ubuntu na Oracleu ima i svoj vatrozid. Kad se spojiš (korak 4), pokreni:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## 4. Spoji se na server

Na Windowsu (PowerShell) ili Macu (Terminal):

```bash
ssh -i putanja/do/ssh-key.key ubuntu@TVOJ_IP
```

## 5. Adresa (DuckDNS)

Na **duckdns.org** upiši javni IP servera pod svoju poddomenu (npr. `bytecrew`) i klikni *update ip*.

## 6. Instaliraj i pokreni

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu && newgrp docker

git clone https://github.com/WARAABOT/Moj-projekt.git
cd Moj-projekt/ai-studio
cp .env.example .env
nano .env        # upiši domenu, lozinku i ključeve (Ctrl+O spremi, Ctrl+X izlaz)

docker compose up -d --build
```

Dok kod nije spojen u glavnu granu, prije `cd` dodaj `git -C Moj-projekt checkout ccr-29b9c9ec-to5dr8`.
Ako je repozitorij privatan, GitHub će tražiti prijavu. Kao lozinku upiši *Personal access token* (GitHub → Settings → Developer settings).

Prvo pokretanje traje 5–10 minuta. Kokoro glas se preuzme sam kod prvog videa (~350 MB).

Otvori `https://bytecrew.duckdns.org` i prijavi se s `DASHBOARD_USER` / `DASHBOARD_PASSWORD`.

## Korisne naredbe

```bash
docker compose logs -f studio     # što agenti rade (Ctrl+C za izlaz)
docker compose restart studio     # nakon promjene .env
git pull && docker compose up -d --build   # nova verzija
```
