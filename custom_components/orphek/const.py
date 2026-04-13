"""Constants for the Orphek integration."""

DOMAIN = "orphek"

CONF_DEVICE_ID = "device_id"
CONF_HOST = "host"
CONF_LOCAL_KEY = "local_key"
CONF_ATOP_EMAIL = "atop_email"
CONF_ATOP_PASSWORD = "atop_password"
CONF_ATOP_COUNTRY_CODE = "atop_country_code"

TUYA_VERSION = 3.4

# ---------- Tuya DP mappings for Orphek OR4-iCon LED Bar ----------
# Standard DPs
DP_SWITCH = 20          # bool: on/off
DP_WORK_MODE = 21       # enum: white, colour, scene, music (Tuya standard, not used by Orphek panel)
DP_BRIGHTNESS = 22      # int 10-1000: base brightness (Tuya standard, effectively always 1000)

# Temperature / fault
DP_TEMPERATURE_C = 101  # int 0-100: current temperature (°C, read-only)
DP_FAULT = 102          # bitmap: fault alarm (read-only)

# LED channel intensities (0-100 each, 6 channels)
DP_CH1 = 103
DP_CH2 = 104
DP_CH3 = 105
DP_CH4 = 106
DP_CH5 = 107
DP_CH6 = 108
DP_CHANNELS = [DP_CH1, DP_CH2, DP_CH3, DP_CH4, DP_CH5, DP_CH6]

CHANNEL_MIN = 0
CHANNEL_MAX = 100

# Mode selection
DP_MODE = 110           # enum: program, quick, sunMoonSync, biorhythm
DP_MODE_RUNNING = 122   # enum (ro): currently running mode

# Schedule / program data (raw, base64-encoded binary)
DP_PROGRAM_MODE = 111   # program schedule (current)
DP_PROGRAM_PRESET = 112 # program schedule (preset/default)
DP_PROGRAM_PREVIEW = 113  # program preview

# Expansion modes (raw, base64-encoded binary)
DP_JELLYFISH = 114      # jellyfish effect config
DP_CLOUDS = 115         # clouds effect config
DP_ACCLIMATION = 116    # acclimation config
DP_LUNAR = 117          # lunar cycle config
DP_BIORHYTHM = 126      # biorhythm schedule
DP_SUN_MOON_SYNC = 127  # sun/moon sync config

# Device settings
DP_DEVICE_TIME = 118    # raw: device clock (24h_flag, year_hi, year_lo, month, day, hour, minute)
DP_HOUR_SYSTEM = 119    # bool: 12/24h toggle
DP_NO_AUTO_SWITCH = 120 # bool: disable auto-recovery
DP_CHANNEL_COUNT = 121  # enum (ro): number of channels ('6','5','4','3','2','1')
DP_QUIET_MODE = 123     # bool: quiet/silent fan mode
DP_TEMP_F = 124         # int 32-212: current temperature (°F, read-only)
DP_TEMP_UNIT = 125      # enum: 'c' or 'f'

# Quick mode preset (raw)
DP_QUICK_PRESET = 109   # quick mode preset data

# Mode enum values
MODES_SELECTABLE = ["program", "quick", "sunMoonSync", "biorhythm"]
MODES_RUNNING = [
    "program", "quick", "jellyfish", "clouds",
    "acclimation", "lunar", "sun_moon", "biorhythm",
]

BRIGHTNESS_MIN = 10
BRIGHTNESS_MAX = 1000

# Embedded Tuya IoT Platform credentials for automatic key retrieval
TUYA_API_KEY = "gcajysgwxv735px5hw74"
TUYA_API_SECRET = "b315e92b136b452292429a0f69bd21d3"
TUYA_API_REGION = "eu"

# Country calling codes for login (sorted by name)
# fmt: off
COUNTRIES: dict[str, str] = {
    "93": "Afghanistan (+93)",
    "355": "Albania (+355)",
    "213": "Algeria (+213)",
    "1684": "American Samoa (+1684)",
    "376": "Andorra (+376)",
    "244": "Angola (+244)",
    "1264": "Anguilla (+1264)",
    "1268": "Antigua and Barbuda (+1268)",
    "54": "Argentina (+54)",
    "374": "Armenia (+374)",
    "297": "Aruba (+297)",
    "61": "Australia (+61)",
    "43": "Austria (+43)",
    "994": "Azerbaijan (+994)",
    "1242": "Bahamas (+1242)",
    "973": "Bahrain (+973)",
    "880": "Bangladesh (+880)",
    "1246": "Barbados (+1246)",
    "375": "Belarus (+375)",
    "32": "Belgium (+32)",
    "501": "Belize (+501)",
    "229": "Benin (+229)",
    "1441": "Bermuda (+1441)",
    "975": "Bhutan (+975)",
    "591": "Bolivia (+591)",
    "387": "Bosnia and Herzegovina (+387)",
    "267": "Botswana (+267)",
    "55": "Brazil (+55)",
    "246": "British Indian Ocean Territory (+246)",
    "1284": "British Virgin Islands (+1284)",
    "673": "Brunei (+673)",
    "359": "Bulgaria (+359)",
    "226": "Burkina Faso (+226)",
    "257": "Burundi (+257)",
    "855": "Cambodia (+855)",
    "237": "Cameroon (+237)",
    "238": "Cape Verde (+238)",
    "1345": "Cayman Islands (+1345)",
    "236": "Central African Republic (+236)",
    "235": "Chad (+235)",
    "56": "Chile (+56)",
    "86": "China (+86)",
    "57": "Colombia (+57)",
    "269": "Comoros (+269)",
    "682": "Cook Islands (+682)",
    "506": "Costa Rica (+506)",
    "385": "Croatia (+385)",
    "5999": "Curacao (+5999)",
    "357": "Cyprus (+357)",
    "420": "Czech Republic (+420)",
    "243": "Democratic Republic of the Congo (+243)",
    "45": "Denmark (+45)",
    "253": "Djibouti (+253)",
    "1767": "Dominica (+1767)",
    "1809": "Dominican Republic (+1809)",
    "535": "Dutch Caribbean (+535)",
    "670": "East Timor (+670)",
    "593": "Ecuador (+593)",
    "20": "Egypt (+20)",
    "503": "El Salvador (+503)",
    "240": "Equatorial Guinea (+240)",
    "291": "Eritrea (+291)",
    "372": "Estonia (+372)",
    "251": "Ethiopia (+251)",
    "500": "Falkland Islands (+500)",
    "298": "Faroe Islands (+298)",
    "691": "Micronesia (+691)",
    "679": "Fiji (+679)",
    "358": "Finland (+358)",
    "33": "France (+33)",
    "594": "French Guiana (+594)",
    "689": "French Polynesia (+689)",
    "241": "Gabon (+241)",
    "220": "Gambia (+220)",
    "995": "Georgia (+995)",
    "49": "Germany (+49)",
    "233": "Ghana (+233)",
    "350": "Gibraltar (+350)",
    "30": "Greece (+30)",
    "299": "Greenland (+299)",
    "1473": "Grenada (+1473)",
    "590": "Guadeloupe (+590)",
    "1671": "Guam (+1671)",
    "502": "Guatemala (+502)",
    "224": "Guinea (+224)",
    "245": "Guinea-Bissau (+245)",
    "592": "Guyana (+592)",
    "509": "Haiti (+509)",
    "504": "Honduras (+504)",
    "852": "Hong Kong (+852)",
    "36": "Hungary (+36)",
    "354": "Iceland (+354)",
    "91": "India (+91)",
    "62": "Indonesia (+62)",
    "964": "Iraq (+964)",
    "353": "Ireland (+353)",
    "972": "Israel (+972)",
    "39": "Italy (+39)",
    "225": "Ivory Coast (+225)",
    "1876": "Jamaica (+1876)",
    "81": "Japan (+81)",
    "962": "Jordan (+962)",
    "254": "Kenya (+254)",
    "686": "Kiribati (+686)",
    "965": "Kuwait (+965)",
    "996": "Kyrgyzstan (+996)",
    "856": "Laos (+856)",
    "371": "Latvia (+371)",
    "961": "Lebanon (+961)",
    "266": "Lesotho (+266)",
    "231": "Liberia (+231)",
    "218": "Libya (+218)",
    "423": "Liechtenstein (+423)",
    "370": "Lithuania (+370)",
    "352": "Luxembourg (+352)",
    "853": "Macau (+853)",
    "261": "Madagascar (+261)",
    "265": "Malawi (+265)",
    "60": "Malaysia (+60)",
    "960": "Maldives (+960)",
    "223": "Mali (+223)",
    "356": "Malta (+356)",
    "692": "Marshall Islands (+692)",
    "596": "Martinique (+596)",
    "222": "Mauritania (+222)",
    "230": "Mauritius (+230)",
    "262": "Mayotte / Reunion (+262)",
    "52": "Mexico (+52)",
    "373": "Moldova (+373)",
    "377": "Monaco (+377)",
    "976": "Mongolia (+976)",
    "382": "Montenegro (+382)",
    "1664": "Montserrat (+1664)",
    "212": "Morocco (+212)",
    "258": "Mozambique (+258)",
    "95": "Myanmar (+95)",
    "264": "Namibia (+264)",
    "674": "Nauru (+674)",
    "977": "Nepal (+977)",
    "31": "Netherlands (+31)",
    "687": "New Caledonia (+687)",
    "64": "New Zealand (+64)",
    "505": "Nicaragua (+505)",
    "227": "Niger (+227)",
    "234": "Nigeria (+234)",
    "683": "Niue (+683)",
    "672": "Norfolk Island (+672)",
    "1670": "Northern Mariana Islands (+1670)",
    "47": "Norway (+47)",
    "968": "Oman (+968)",
    "92": "Pakistan (+92)",
    "680": "Palau (+680)",
    "970": "Palestine (+970)",
    "507": "Panama (+507)",
    "675": "Papua New Guinea (+675)",
    "595": "Paraguay (+595)",
    "51": "Peru (+51)",
    "63": "Philippines (+63)",
    "48": "Poland (+48)",
    "351": "Portugal (+351)",
    "1787": "Puerto Rico (+1787)",
    "974": "Qatar (+974)",
    "389": "North Macedonia (+389)",
    "242": "Republic of the Congo (+242)",
    "40": "Romania (+40)",
    "7": "Russia / Kazakhstan (+7)",
    "250": "Rwanda (+250)",
    "1869": "Saint Kitts and Nevis (+1869)",
    "1758": "Saint Lucia (+1758)",
    "508": "Saint Pierre and Miquelon (+508)",
    "1784": "Saint Vincent and the Grenadines (+1784)",
    "685": "Samoa (+685)",
    "378": "San Marino (+378)",
    "239": "Sao Tome and Principe (+239)",
    "966": "Saudi Arabia (+966)",
    "221": "Senegal (+221)",
    "381": "Serbia (+381)",
    "248": "Seychelles (+248)",
    "232": "Sierra Leone (+232)",
    "65": "Singapore (+65)",
    "1721": "Sint Maarten (+1721)",
    "421": "Slovakia (+421)",
    "386": "Slovenia (+386)",
    "677": "Solomon Islands (+677)",
    "252": "Somalia (+252)",
    "27": "South Africa (+27)",
    "82": "South Korea (+82)",
    "34": "Spain (+34)",
    "94": "Sri Lanka (+94)",
    "597": "Suriname (+597)",
    "268": "Eswatini (+268)",
    "46": "Sweden (+46)",
    "41": "Switzerland (+41)",
    "886": "Taiwan (+886)",
    "992": "Tajikistan (+992)",
    "255": "Tanzania (+255)",
    "66": "Thailand (+66)",
    "228": "Togo (+228)",
    "690": "Tokelau (+690)",
    "676": "Tonga (+676)",
    "1868": "Trinidad and Tobago (+1868)",
    "216": "Tunisia (+216)",
    "90": "Turkey (+90)",
    "993": "Turkmenistan (+993)",
    "1649": "Turks and Caicos Islands (+1649)",
    "688": "Tuvalu (+688)",
    "1340": "U.S. Virgin Islands (+1340)",
    "256": "Uganda (+256)",
    "380": "Ukraine (+380)",
    "971": "United Arab Emirates (+971)",
    "44": "United Kingdom (+44)",
    "1": "United States / Canada (+1)",
    "598": "Uruguay (+598)",
    "998": "Uzbekistan (+998)",
    "678": "Vanuatu (+678)",
    "379": "Vatican (+379)",
    "58": "Venezuela (+58)",
    "84": "Vietnam (+84)",
    "681": "Wallis and Futuna (+681)",
    "967": "Yemen (+967)",
    "260": "Zambia (+260)",
    "263": "Zimbabwe (+263)",
}
# fmt: on
