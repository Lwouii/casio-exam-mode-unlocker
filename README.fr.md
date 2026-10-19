# casio-exam-mode-unlocker

**Langue :** [English](README.md) | Français

Utilitaire autonome pour Linux permettant de sortir du Mode Examen sur les calculatrices graphiques Casio de première génération via USB. Il contourne le blocage du pilote `CESG64.sys` sur les versions récentes de Windows et fournit une solution native pour combler l'absence de logiciel officiel sous Linux.

## Matériel compatible

Calculatrices utilisant l'interface USB Casio (`07cf:6101`) :
- Graph 35+E (première génération)
- Graph 75+E
- fx-9750GII
- fx-9860GII

### Modèles récents en stockage de masse

Les calculatrices récentes ne nécessitent pas ce script :
- Graph 35+E II
- Graph 90+E
- fx-CG50

Ces modèles fonctionnent comme une clé USB standard. Pour quitter le Mode Examen :
1. Branchez la calculatrice à l'ordinateur avec un câble USB.
2. Sélectionnez le mode clé USB (touche F1 sur la calculatrice).
3. Ouvrez le lecteur monté dans votre gestionnaire de fichiers, puis créez, copiez ou supprimez un petit fichier quelconque.
4. Éjectez proprement le lecteur et débranchez le câble. La calculatrice quitte automatiquement le Mode Examen.

## Prérequis

- Python 3 (bibliothèque standard uniquement : `ctypes`, `sys`). Aucun paquet `pip` requis.
- `libusb-1.0` (installé via `libusb-1.0-0` sur Debian, Ubuntu et Linux Mint).

## Utilisation

Branchez la calculatrice à l'ordinateur avec un câble USB, allumez-la et exécutez :

```bash
sudo python3 unlock_casio.py
```

Les privilèges root sont requis car Linux restreint par défaut l'accès en écriture directe aux périphériques de caractères USB (`/dev/bus/usb/...`).

### Utilisation sans sudo

Pour autoriser les utilisateurs du groupe `plugdev` à accéder à la calculatrice sans `sudo`, configurez une règle udev :

```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="07cf", ATTR{idProduct}=="6101", MODE="0660", GROUP="plugdev"' | sudo tee /etc/udev/rules.d/99-casio.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Débranchez puis rebranchez le câble USB, puis exécutez :

```bash
python3 unlock_casio.py
```

## Dépannage

- **`Error: calculator not found or permission denied. Run with sudo.`**
  Le script ne parvient pas à ouvrir le périphérique USB `07cf:6101`. Vérifiez que la calculatrice est allumée et correctement branchée. Si le câble est bien branché, vérifiez que vous exécutez le script avec `sudo` ou que la règle udev ci-dessus est installée.
- **`Error: failed to load libusb: ...`**
  La bibliothèque partagée système `libusb-1.0` est absente. Installez-la sur Debian, Ubuntu ou Linux Mint avec `sudo apt install libusb-1.0-0`.
- **`Error: unexpected response to ENQ` ou `Error: unexpected response to CAN`**
  La calculatrice a renvoyé une réponse inattendue lors de l'échange. Vérifiez que votre modèle utilise bien l'identifiant `07cf:6101` et qu'elle se trouve bien verrouillée en Mode Examen.

## Compatibilité système et limites

- **Linux :** Entièrement testé et fonctionnel nativement. Ne nécessite aucun pilote tiers ni module noyau particulier.
- **Windows :** Non testé avec ce script. Sur Windows 10 et 11, l'intégrité de la mémoire (Core Isolation) bloque le pilote officiel Casio (`CESG64.sys`) avec le message "Un pilote ne peut pas être chargé sur cet appareil : CESG64.sys". Exécuter ce script Python sous Windows nécessiterait de remplacer le pilote bloqué par WinUSB via Zadig et de placer `libusb-1.0.dll` dans le répertoire du script.
- **macOS :** Non testé avec ce script. Son exécution sous macOS nécessite l'installation de `libusb` (par exemple via `brew install libusb`).

## Rétro-ingénierie

L'utilitaire officiel Windows (`Exam_Mode_Unlocker_Ver.1.00.exe`) est un installeur InstallShield encapsulant le pilote bloqué `CESG64.sys`. Pour identifier le protocole de communication, nous avons analysé le binaire officiel macOS (`Exam Mode Unlocker.app`).

1. Extraction du binaire Mach-O x86_64 situé dans `Contents/MacOS/Exam Mode Unlocker`.
2. Inspection de la table des symboles (`LC_SYMTAB`) et identification des fonctions du fichier objet `USBPipes.o` :
   - `USBPipes::PerformUnlock`
   - `USBPipes::FindPipes`
   - `request_unlock_command`
3. Désassemblage de la fonction `PerformUnlock` avec `objdump`, révélant la séquence des transferts USB :
   - Réquisition de l'interface 0 sur le périphérique `07cf:6101`.
   - Réinitialisation des canaux sur les endpoints `0x01` (Bulk OUT) et `0x82` (Bulk IN).
   - Écriture de 6 octets sur l'endpoint `0x01` : `\x0500070` (ENQ).
   - Lecture de 6 octets sur l'endpoint `0x82` : attente de `\x0600070` (ACK).
   - Écriture de 6 octets sur l'endpoint `0x01` : `\x1800070` (CAN / déverrouillage).
   - Lecture de 6 octets sur l'endpoint `0x82` : attente de `\x0600070` (ACK).

La calculatrice quitte le Mode Examen dès la réception du second paquet ACK.
