import random

SUSPECTS = ["Le Jardinier", "Le Majordome", "La Comtesse", "La Gouvernante", "Le Cuisinier", "Le Chauffeur"]
ARMES = ["Pistolet", "Pelle", "Couteau", "Tournevis", "Vase", "Hache"]
SALLES = ["Serre", "Bureau", "Chambre", "Salle à manger", "Hall", "Salon", "Cave", "Entrée", "Cuisine"]

PORTES = {
    "Serre": ["Bureau", "Salon"],
    "Bureau": ["Hall", "Serre", "Chambre"],
    "Chambre": ["Bureau", "Salle à manger"],
    "Salon": ["Hall", "Serre", "Cave"],
    "Hall": ["Bureau", "Salon", "Salle à manger", "Entrée"],
    "Salle à manger": ["Hall", "Chambre", "Cuisine"],
    "Cave": ["Salon", "Entrée"],
    "Entrée": ["Hall", "Cave", "Cuisine"],
    "Cuisine": ["Entrée", "Salle à manger"]
}

PASSAGES = {
    "Serre": "Cuisine",
    "Cuisine": "Serre",
    "Chambre": "Cave",
    "Cave": "Chambre"
}

PA_PAR_TOUR = 3

def distribuer(joueurs):
    enveloppe = {
        "suspect": random.choice(SUSPECTS), 
        "arme": random.choice(ARMES), 
        "salle": random.choice(SALLES)
    }

    cartes = SUSPECTS + ARMES + SALLES
    cartes.remove(enveloppe["suspect"])
    cartes.remove(enveloppe["arme"])
    cartes.remove(enveloppe["salle"])

    random.shuffle(cartes)

    mains = {}
    for pseudo in joueurs:
        mains[pseudo] = []

    par_joueur = len(cartes) // len(joueurs)
    total = par_joueur * len(joueurs)
    a_distribuer = cartes[:total]
    visibles = cartes[total:]

    for i, carte in enumerate(a_distribuer):
        pseudo = joueurs[i % len(joueurs)]
        mains[pseudo].append(carte)

    return enveloppe, mains, visibles


def placer_pions(joueurs):
    positions_suspects = {}
    positions_armes = {}
    positions_joueurs = {}

    for suspect in SUSPECTS:
        positions_suspects[suspect] = "Hall"

    for arme in ARMES:
        positions_armes[arme] = "Hall"

    SALLES_SANS_HALL = SALLES.copy()
    SALLES_SANS_HALL.remove("Hall")

    salles_tirees = random.sample(SALLES_SANS_HALL, len(joueurs))

    for i, pseudo in enumerate(joueurs):
        positions_joueurs[pseudo] = salles_tirees[i]

    return positions_suspects, positions_armes, positions_joueurs


def cout_deplacement(depart, arrivee):
    if arrivee in PORTES[depart]:
        return 1
    if PASSAGES.get(depart) == arrivee:
        return 2
    return None


def passer_au_tour_suivant(salon):
    ordre = salon["ordre"]
    index = ordre.index(salon["joueur_actif"])
    for decalage in range(1, len(ordre) + 1):
        candidat = ordre[(index + decalage) % len(ordre)]
        if candidat not in salon["elimines"]:
            salon["joueur_actif"] = candidat
            break
    salon["pa"] = PA_PAR_TOUR
    salon["suppose_ce_tour"] = False


def trouver_repondant(salon, auteur, suspect, arme, salle):
    ordre = salon["ordre"]
    debut = ordre.index(auteur)
    for decalage in range(1, len(ordre)):
        candidat = ordre[(debut + decalage) % len(ordre)]
        contredisent = [c for c in salon["mains"][candidat] if c in [suspect, arme, salle]]
        if contredisent:
            return candidat, contredisent
    return None, []


### VÉRIFICATION DE LA LOGIQUE DU PLAN ###

def verifier_portes():
    for salle, voisines in PORTES.items():
        for voisine in voisines:
            assert salle in PORTES[voisine], "PLAN: Erreur de logique des portes."

def verifier_passages():
    for salle, passage in PASSAGES.items():
        assert PASSAGES[passage] == salle, "PLAN: Erreur de logique des passages."

verifier_portes()
verifier_passages()