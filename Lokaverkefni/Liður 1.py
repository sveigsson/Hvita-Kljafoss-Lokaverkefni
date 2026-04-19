hvita_kljafoss = {
    "heiti": "Hvítá við Kljáfoss",
    "flatarmal_km2": 1719.981,
    "medalhaed_m": 666.337,
    "midgildi_haedar_m": 613.768,
    "joklasvaedi_km2": 325.076,
    "joklahlutfall": 0.189,
    "medalhalli_m_km": 100.468,
    "stoduvatnahlutfall": 0.007,
    "berggrunnur": "Að mestu eldgosaberg, líklega aðallega basískt gosberg.",
    "yfirbordsjardfraedi": "Yfirborð einkennist líklega af hreyfanlegum setlögum og lausu efni.",
    "jardvegur": {
        "sandur": 0.588,
        "silt": 0.259,
        "leir": 0.156,
    },
    "landthekja": {
        "berangur": 0.454,
        "kjarr_molendi": 0.263,
        "joklar": 0.189,
        "stoduvotn": 0.007,
    },
    "mannvirki_og_ahrif": "Vatnasviðið virðist lítið eða ekkert raskað samkvæmt gagnasafninu.",
}


def prosent(gildi):
    return f"{gildi * 100:.1f}%"


print(f"Samantekt fyrir {hvita_kljafoss['heiti']}")
print("-" * 40)
print(f"Flatarmál: {hvita_kljafoss['flatarmal_km2']:.1f} km²")
print(f"Meðalhæð: {hvita_kljafoss['medalhaed_m']:.1f} m y.s.")
print(f"Miðgildi hæðar: {hvita_kljafoss['midgildi_haedar_m']:.1f} m y.s.")
print(f"Meðalhalli: {hvita_kljafoss['medalhalli_m_km']:.1f} m/km")
print(
    f"Jöklar: {hvita_kljafoss['joklasvaedi_km2']:.1f} km² "
    f"({prosent(hvita_kljafoss['joklahlutfall'])})"
)
print(f"Stöðuvötn: {prosent(hvita_kljafoss['stoduvatnahlutfall'])}")
print(f"Berggrunnur: {hvita_kljafoss['berggrunnur']}")
print(f"Yfirborðsjarðfræði: {hvita_kljafoss['yfirbordsjardfraedi']}")
print(
    "Jarðvegur: "
    f"sandur {prosent(hvita_kljafoss['jardvegur']['sandur'])}, "
    f"silt {prosent(hvita_kljafoss['jardvegur']['silt'])}, "
    f"leir {prosent(hvita_kljafoss['jardvegur']['leir'])}"
)
print(
    "Gróður og landþekja: "
    f"berangur {prosent(hvita_kljafoss['landthekja']['berangur'])}, "
    f"kjarr/mólendi {prosent(hvita_kljafoss['landthekja']['kjarr_molendi'])}, "
    f"jöklar {prosent(hvita_kljafoss['landthekja']['joklar'])}, "
    f"stöðuvötn {prosent(hvita_kljafoss['landthekja']['stoduvotn'])}"
)
print(f"Mannvirki og áhrif: {hvita_kljafoss['mannvirki_og_ahrif']}")
