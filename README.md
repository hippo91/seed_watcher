# seed_watcher
Watch the status of your seedbox using leds and raspberry.

**seed_watcher** will print on stdout different informations concerning your seed box :
  - localization status : ok if you hide your localization behind a vpn
  - download speed.

Moreover if **seed_watcher** is launch from a *raspberry pi* (whatever version having access to GPIO),
the corresponding informations will be transcripted into led blinking.

If your localization is elsewhere than your country, green led will be lightning up.
Otherwise a red led will be blinking.

A blue led will blink with a frequency that is inversely proportional to the download speed.

## Installation
Just download or clone this repository :

    git clone https://github.com/hippo91/seed_watcher.git
  
Then type :

    cd seed_watcher; pip install .
 
