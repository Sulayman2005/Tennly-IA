// Logique visuelle partagée pour représenter un joueur/une joueuse : vraie
// photo quand elle est connue (Player.photoUrl, voir ml-service/
// import_player_photos_wikipedia.py), sinon avatar en dégradé déterministe +
// petit drapeau image ; et identité visuelle (dégradé + accent) selon la
// surface du match.
// Utilisé par MatchCard.vue (liste /matchs) et MatchDetailView.vue (fiche
// détaillée) — factorisé ici pour que les deux restent visuellement
// identiques sans dupliquer la palette à deux endroits qui finiraient par
// diverger.

// Initiales façon "maillot" : prénom + nom de famille uniquement (jamais un
// éventuel deuxième prénom), pour rester lisible dans un avatar rond même
// sur les noms à rallonge ("Daniel Adolfo Vallejo" → "DV", pas "DAV").
export function initials(fullName) {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

// Dégradé d'avatar déterministe par joueur (même joueur = même dégradé
// d'une carte à l'autre, d'une visite à l'autre) : on hache le nom complet
// plutôt que de piocher au hasard, pour que Carlos Alcaraz ait toujours le
// même avatar. Palette resserrée sur des tons "pierre précieuse" proches de
// l'identité existante (teal + lime) pour ne jamais jurer avec le fond des
// cartes, plutôt que des couleurs arbitraires.
const AVATAR_GRADIENTS = [
  ['#1f8a6b', '#c7ff3c'], // signature teal → lime
  ['#0071e3', '#0a2c2d'], // bleu dur → teal foncé
  ['#c1652e', '#f5c451'], // terre battue → or
  ['#6b3fa0', '#d946a0'], // prune → rose
  ['#0a2c2d', '#4fd1c5'], // teal foncé → glace
  ['#2f4858', '#8aa399'], // ardoise → olive
]

function hash(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0
  return Math.abs(h)
}

export function avatarGradient(fullName) {
  const [from, to] = AVATAR_GRADIENTS[hash(fullName) % AVATAR_GRADIENTS.length]
  return { background: `linear-gradient(135deg, ${from}, ${to})` }
}

// Vraie photo disponible pour ce joueur ? (Player.photoUrl, voir
// ml-service/import_player_photos_wikipedia.py — reste vide tant qu'aucune
// photo sous licence libre n'a été trouvée pour ce joueur précis). Un
// simple champ non-vide suffit ici : le composant appelant est responsable
// de basculer sur l'avatar initiales en repli si l'image échoue au
// chargement (URL Wikimedia cassée/renommée) — voir onPhotoError() dans
// MatchCard.vue / MatchDetailView.vue.
export function hasPhoto(player) {
  return typeof player?.photoUrl === 'string' && player.photoUrl.length > 0
}

// Drapeau à partir du code pays (voir Player.php, countryCode) — codes à 3
// lettres façon IOC/ITF, casse non fiable ("USA" vs "usa" selon les
// joueurs), d'où le .toUpperCase(). Volontairement pas de repli par défaut
// pour un code absent de la liste (joueurs russes/biélorusses notamment,
// qui jouent sans drapeau) : pas de drapeau plutôt qu'un mauvais drapeau.
//
// Une vraie petite image (flagcdn.com, alpha-2) plutôt qu'un emoji drapeau :
// Windows ne fournit aucun glyphe pour les emoji drapeau (séquences
// d'indicateurs régionaux) dans Chrome/Edge — testé en conditions réelles,
// ça affichait un rond blanc vide sur la machine Windows du projet. Une image
// s'affiche pareil partout, quel que soit l'OS.
const COUNTRY_ALPHA2 = {
  ESP: 'es', FRA: 'fr', CHN: 'cn', USA: 'us', GER: 'de', ARG: 'ar',
  GBR: 'gb', ITA: 'it', HUN: 'hu', POL: 'pl', BEL: 'be', INA: 'id',
  CZE: 'cz', UKR: 'ua', AUT: 'at', THA: 'th', UZB: 'uz', MON: 'mc',
  PHI: 'ph', KAZ: 'kz', ROU: 'ro', JPN: 'jp', PER: 'pe', NED: 'nl',
  SVK: 'sk', CRO: 'hr', AUS: 'au', SUI: 'ch', CAN: 'ca', BRA: 'br',
  RSA: 'za', SRB: 'rs', SWE: 'se', NOR: 'no', DEN: 'dk', FIN: 'fi',
  GRE: 'gr', POR: 'pt', TUR: 'tr', EGY: 'eg', MAR: 'ma', TUN: 'tn',
  CHI: 'cl', COL: 'co', MEX: 'mx', IND: 'in', KOR: 'kr', TPE: 'tw',
  HKG: 'hk', SGP: 'sg', NZL: 'nz', IRL: 'ie', BUL: 'bg', SLO: 'si',
  SVN: 'si', LAT: 'lv', LTU: 'lt', EST: 'ee', GEO: 'ge', ARM: 'am',
  AZE: 'az', BLR: 'by', RUS: 'ru', ISR: 'il', QAT: 'qa', UAE: 'ae',
  KSA: 'sa', NGA: 'ng', KEN: 'ke', ALG: 'dz', CMR: 'cm', CIV: 'ci',
  SEN: 'sn', PAR: 'py', MDA: 'md', ISL: 'is', LUX: 'lu',
}

export function flagUrl(countryCode) {
  if (!countryCode) return null
  const a2 = COUNTRY_ALPHA2[countryCode.toUpperCase()]
  return a2 ? `https://flagcdn.com/48x36/${a2}.png` : null
}

// Identité visuelle par surface — chaque surface a désormais SON dégradé de
// fond (pas seulement un halo par-dessus un fond vert fixe partagé par
// tous : demande explicite du 09/09/2026, "pas un seul fond vert je sais
// plus de peps sur la page"). Choix ancrés dans la vraie identité de chaque
// surface plutôt qu'arbitraires : bleu nuit → bleu dur pour le dur (courts
// durs à dominante bleue sur le circuit, ex. US Open/Australian Open),
// terre cuite → ocre pour la terre battue (Roland-Garros), vert profond →
// vert gazon pour le gazon (Wimbledon, seule surface qui garde le vert
// historique de la marque), et une variante violette pour l'indoor
// (éclairage de salle). --terre/--clay existent déjà comme tokens globaux
// (voir tokens.css, section HomeView) : réutilisés ici tels quels pour la
// terre battue plutôt que d'inventer une deuxième paire de couleurs terre
// battue qui finirait par diverger.
//
// Correctif du 09/09/2026 : les clés de cette table (et de l'ancienne
// SURFACE_ACCENTS qu'elle remplace) étaient 'dur' / 'terre' / 'gazon', alors
// que Surface::TERRE_BATTUE (voir backend/src/Entity/Enum/Surface.php) se
// sérialise en 'terre_battue' — la clé 'terre' ne correspondait donc à
// AUCUN match réel. Tous les matchs sur terre battue (et sur indoor, absent
// de la table) retombaient silencieusement sur l'accent gazon par défaut,
// ce qui explique une bonne partie du "tout est vert" repéré : pas
// seulement un choix de design daté, un vrai bug d'accord de clé.
const SURFACE_GRADIENTS = {
  dur: ['#04213f', '#0071e3'],
  terre_battue: ['#6e3618', '#c1652e'],
  gazon: ['#0f3d3e', '#3ea56b'],
  indoor: ['#241b3d', '#6b3fa0'],
}

const SURFACE_LABELS = {
  dur: 'Dur',
  terre_battue: 'Terre battue',
  gazon: 'Gazon',
  indoor: 'Indoor',
}

export function surfaceLabel(surface) {
  return SURFACE_LABELS[surface] ?? 'Surface'
}

function hexToRgba(hex, alpha) {
  const n = parseInt(hex.slice(1), 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// Variables CSS à poser en :style sur le conteneur — fond dégradé propre à
// la surface (--surface-from/--surface-to) + halo et ombre assortis
// (--surface-glow/--surface-shadow/--surface-tint) — voir .match-card
// (MatchCard.vue) et .face-off (MatchDetailView.vue), qui consomment ces
// variables.
export function surfaceCardVars(surface) {
  const [from, to] = SURFACE_GRADIENTS[surface] ?? SURFACE_GRADIENTS.dur
  const accent = to
  return {
    '--surface-from': from,
    '--surface-to': to,
    '--surface-glow': hexToRgba(accent, 0.4),
    '--surface-shadow': hexToRgba(accent, 0.38),
    '--surface-tint': hexToRgba(accent, 0.18),
  }
}
