from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import random
import string
import secrets

import game

app = FastAPI()

salons = {}

class DemandeSalon(BaseModel):
    pseudo: str

class DemandeDeplacement(BaseModel):
    destination: str

class DemandeSupposition(BaseModel):
    suspect: str
    arme: str

class DemandeReponse(BaseModel):
    carte: str

class DemandeAccusation(BaseModel):
    suspect: str
    arme: str
    salle: str

@app.get("/salon/{code}")
async def voir_salon(code: str):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]

    attend = None
    if salon.get("supposition") is not None:
        attend = salon["supposition"]["repondant"]

    enveloppe = None
    if salon["etat"] == "fini":
        enveloppe = salon["enveloppe"]

    salon_public = {
        "hote": salon["hote"], 
        "joueurs": salon["joueurs"], 
        "etat": salon["etat"], 
        "visibles": salon.get("visibles", []),
        "positions_suspects": salon.get("positions_suspects", {}),
        "positions_armes": salon.get("positions_armes", {}),
        "positions_joueurs": salon.get("positions_joueurs", {}),
        "joueur_actif": salon.get("joueur_actif"),
        "pa": salon.get("pa", 0),
        "journal": salon.get("journal", []),
        "suspects": game.SUSPECTS,
        "armes": game.ARMES,
        "attend": attend,
        "elimines": salon.get("elimines", []),
        "gagnant": salon.get("gagnant"),
        "salles": game.SALLES,
        "enveloppe": enveloppe
    }
    return salon_public

def generer_code():
    return(''.join(random.choices(string.ascii_uppercase, k=4)))

@app.post("/salon")
async def creer_salon(demande: DemandeSalon):
    code = generer_code()
    jeton = secrets.token_hex(16)
    while code in salons:
        code = generer_code()
    salons[code] = {"hote": demande.pseudo, "joueurs": [demande.pseudo], "jetons": {jeton: demande.pseudo}, "etat": "attente"}
    return {"code": code, "jeton": jeton}

@app.post("/salon/{code}/rejoindre")
async def rejoindre_salon(code: str, demande: DemandeSalon):
    code = code.upper()
    jeton = secrets.token_hex(16)
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if salon["etat"] != "attente":
        raise HTTPException(status_code=400, detail="La partie a déjà commencé, essaye de rejoindre une autre enquête.")
    elif len(salon["joueurs"]) >= 6:
        raise HTTPException(status_code=400, detail="Le salon est plein (6 joueurs maximum), ils devraient parvenir à trouver le coupable...")
    elif demande.pseudo in salon["joueurs"]:
        raise HTTPException(status_code=409, detail="Le pseudo est déjà utilisé, n'essaye pas d'usurper l'identité d'un autre détective...")
    else:
        salon["joueurs"].append(demande.pseudo)
        salon["jetons"][jeton] = demande.pseudo
    return {"joueurs": salon["joueurs"], "jeton": jeton}

@app.get("/salon/{code}/moi")
async def qui_suis_je(code: str, jeton: str):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas")
    pseudo = salon["jetons"][jeton]
    return {"pseudo": pseudo, "hote": salon["hote"]==pseudo}

@app.post("/salon/{code}/lancer")
async def lancer_partie(code: str, jeton: str):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas.")
    pseudo = salon["jetons"][jeton]
    if pseudo != salon["hote"]:
        raise HTTPException(status_code=403, detail="Seul l'hôte peut lancer la partie.")
    if salon["etat"] != "attente":
        raise HTTPException(status_code=400, detail="La partie est déjà lancée.")
    if len(salon["joueurs"]) < 2:
        raise HTTPException(status_code=400, detail="Il faut au moins 2 joueurs pour lancer la partie.")

    enveloppe, mains, visibles = game.distribuer(salon["joueurs"])

    salon["enveloppe"] = enveloppe
    salon["mains"] = mains
    salon["visibles"] = visibles

    positions_suspects, positions_armes, positions_joueurs = game.placer_pions(salon["joueurs"])

    salon["positions_suspects"] = positions_suspects
    salon["positions_armes"] = positions_armes
    salon["positions_joueurs"] = positions_joueurs

    ordre = salon["joueurs"].copy()
    random.shuffle(ordre)
    salon["ordre"] = ordre
    salon["joueur_actif"] = ordre[0]
    salon["pa"] = game.PA_PAR_TOUR

    salon["supposition"] = None
    salon["suppose_ce_tour"] = False
    salon["journal"] = []
    salon["reponses"] = {}

    salon["elimines"] = []
    salon["gagnant"] = None

    salon["etat"] = "lance"

    return {"etat": salon["etat"]}

@app.get("/salon/{code}/ma-main")
async def ma_main(code: str, jeton: str):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas.")
    if salon["etat"] != "lance":
        raise HTTPException(status_code=400, detail="La partie n'est pas encore lancée.")
    pseudo = salon["jetons"][jeton]

    return {"cartes": salon["mains"][pseudo]}

@app.get("/salon/{code}/options")
async def options(code: str, jeton: str):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas.")
    if salon["etat"] != "lance":
        raise HTTPException(status_code=400, detail="La partie n'est pas encore lancée.")
    pseudo = salon["jetons"][jeton]
    if salon["supposition"] is not None or pseudo != salon["joueur_actif"]:
        return {"options": [], "peut_supposer": False, "peut_accuser": False}

    position = salon["positions_joueurs"][pseudo]

    liste = []
    for salle in game.SALLES:
        cout = game.cout_deplacement(position, salle)
        if cout is not None and cout <= salon["pa"]:
            liste.append({"salle": salle, "cout": cout})

    peut_supposer = salon["pa"] >= 2 and not salon["suppose_ce_tour"]
    peut_accuser = position == "Hall" and salon["pa"] >= 1

    return {"options": liste, "peut_supposer": peut_supposer, "peut_accuser": peut_accuser}

@app.post("/salon/{code}/deplacer")
async def deplacer(code: str, jeton: str, demande: DemandeDeplacement):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas.")
    if salon["etat"] != "lance":
        raise HTTPException(status_code=400, detail="La partie n'est pas encore lancée.")
    pseudo = salon["jetons"][jeton]
    if pseudo != salon["joueur_actif"]:
        raise HTTPException(status_code=403, detail="Ce n'est pas ton tour détective...")

    if salon["supposition"] is not None:
        raise HTTPException(status_code=409, detail="Une supposition attend une réponse.")

    cout = game.cout_deplacement(salon["positions_joueurs"][pseudo], demande.destination)
    if cout is None:
        raise HTTPException(status_code=400, detail="Déplacement impossible.")
    elif cout > salon["pa"]:
        raise HTTPException(status_code=400, detail="Pas assez de Points d'Action.")
    else:
        salon["positions_joueurs"][pseudo] = demande.destination
        salon["pa"] -= cout

    if salon["pa"] == 0:
        game.passer_au_tour_suivant(salon)

    return {"pa": salon["pa"]}

@app.post("/salon/{code}/finir-tour")
async def finir_tour(code: str, jeton: str):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas.")
    if salon["etat"] != "lance":
        raise HTTPException(status_code=400, detail="La partie n'est pas encore lancée.")
    pseudo = salon["jetons"][jeton]
    if pseudo != salon["joueur_actif"]:
        raise HTTPException(status_code=403, detail="Ce n'est pas ton tour détective...")

    if salon["supposition"] is not None:
        raise HTTPException(status_code=409, detail="Une supposition attend une réponse.")

    game.passer_au_tour_suivant(salon)

    return {"pa": salon["pa"]}

@app.post("/salon/{code}/supposer")
async def supposer(code: str, jeton: str, demande: DemandeSupposition):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas.")
    if salon["etat"] != "lance":
        raise HTTPException(status_code=400, detail="La partie n'est pas encore lancée.")
    pseudo = salon["jetons"][jeton]
    if pseudo != salon["joueur_actif"]:
        raise HTTPException(status_code=403, detail="Ce n'est pas ton tour détective...")
    if salon["supposition"] is not None:
        raise HTTPException(status_code=409, detail="Une supposition est déjà en cours.")
    if salon["suppose_ce_tour"] == True:
        raise HTTPException(status_code=400, detail="Tu as déjà fait une supposition pour ce tour.")
    if salon["pa"] < 2:
        raise HTTPException(status_code=400, detail="Tu n'as pas assez de Points d'Action.")
    if demande.suspect not in game.SUSPECTS or demande.arme not in game.ARMES:
        raise HTTPException(status_code=400, detail="Le suspect ou l'arme n'est pas dans la liste.")

    salle = salon["positions_joueurs"][pseudo]
    salon["positions_suspects"][demande.suspect] = salle
    salon["positions_armes"][demande.arme] = salle
    salon["pa"] -= 2
    salon["suppose_ce_tour"] = True
    salon["reponses"].pop(pseudo, None)

    salon["journal"].append(f"{pseudo} suppose : {demande.suspect} avec {demande.arme}, dans {salle}")

    repondant, cartes = game.trouver_repondant(salon, pseudo, demande.suspect, demande.arme, salle)

    if repondant is None:
        salon["journal"].append(f"Personne n'a pu contredire {pseudo}")
        salon["reponses"][pseudo] = {"repondant": None, "carte": None}
        if salon["pa"] == 0:
            game.passer_au_tour_suivant(salon)

    else:
        salon["supposition"] = {
            "auteur": pseudo,
            "suspect": demande.suspect,
            "arme": demande.arme,
            "salle": salle,
            "repondant": repondant,
            "cartes_possibles": cartes
        }

    return {"pa": salon["pa"]}

@app.get("/salon/{code}/supposition")
async def supposition(code: str, jeton: str):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas.")
    if salon["etat"] != "lance":
        raise HTTPException(status_code=400, detail="La partie n'est pas encore lancée.")
    pseudo = salon["jetons"][jeton]

    supp = salon["supposition"]
    if supp is None or supp["repondant"] != pseudo:
        return {"a_repondre": False}

    return {
        "a_repondre": True,
        "auteur": supp["auteur"],
        "suspect": supp["suspect"],
        "arme": supp["arme"],
        "salle": supp["salle"],
        "cartes": supp["cartes_possibles"]
    }

@app.post("/salon/{code}/repondre")
async def repondre(code: str, jeton: str, demande: DemandeReponse):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas.")
    if salon["etat"] != "lance":
        raise HTTPException(status_code=400, detail="La partie n'est pas encore lancée.")
    pseudo = salon["jetons"][jeton]

    supp = salon["supposition"]
    if supp is None:
        raise HTTPException(status_code=400, detail="Aucune supposition en attente.")
    if pseudo != supp["repondant"]:
        raise HTTPException(status_code=403, detail="Ce n'est pas à toi de répondre.")
    if demande.carte not in supp["cartes_possibles"]:
        raise HTTPException(status_code=400, detail="Tu ne peux pas montrer cette carte")

    auteur = supp["auteur"]
    salon["reponses"][auteur] = {"repondant": pseudo, "carte": demande.carte}
    salon["journal"].append(f"{pseudo} a montré une carte à {auteur}.")
    salon["supposition"] = None

    if salon["pa"] == 0:
        game.passer_au_tour_suivant(salon)

    return {"ok": True}

@app.get("/salon/{code}/ma-reponse")
async def ma_reponse(code: str, jeton: str):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas.")
    if salon["etat"] != "lance":
        raise HTTPException(status_code=400, detail="La partie n'est pas encore lancée.")
    pseudo = salon["jetons"][jeton]

    return {"reponse": salon["reponses"].get(pseudo)}

@app.post("/salon/{code}/accuser")
async def accuser(code: str, jeton: str, demande: DemandeAccusation):
    code = code.upper()
    if code not in salons:
        raise HTTPException(status_code=404, detail="Ce salon n'existe pas, tu t'es trompé de piste détective...")
    salon = salons[code]
    if jeton not in salon["jetons"]:
        raise HTTPException(status_code=401, detail="Ce jeton n'existe pas.")
    if salon["etat"] != "lance":
        raise HTTPException(status_code=400, detail="La partie n'est pas encore lancée.")
    pseudo = salon["jetons"][jeton]
    if pseudo != salon["joueur_actif"]:
        raise HTTPException(status_code=403, detail="Ce n'est pas ton tour détective...")
    if salon["supposition"] is not None:
        raise HTTPException(status_code=409, detail="Une supposition attend une réponse.")
    if salon["positions_joueurs"][pseudo] != "Hall":
        raise HTTPException(status_code=400, detail="Il faut être dans le Hall pour faire une accusation.")
    if salon["pa"] < 1:
        raise HTTPException(status_code=400, detail="Pas assez de Points d'Action.")
    if demande.suspect not in game.SUSPECTS or demande.arme not in game.ARMES or demande.salle not in game.SALLES:
        raise HTTPException(status_code=400, detail="Suspect, arme ou salle inconnus.")

    enveloppe = salon["enveloppe"]
    juste = (
        demande.suspect == enveloppe["suspect"]
        and demande.arme == enveloppe["arme"]
        and demande.salle == enveloppe["salle"]
    )

    if juste:
        salon["etat"] = "fini"
        salon["gagnant"] = pseudo
        salon["journal"].append(f"{pseudo} a réussi à déceler le crime !")
        return {"juste": True}

    salon["elimines"].append(pseudo)
    salon["journal"].append(f"{pseudo} a fait une fausse accusation et est éliminé...")
    
    if len(salon["elimines"]) == len(salon["joueurs"]):
        salon["etat"] = "fini"
        salon["journal"].append("Personne n'a trouvé la solution...")
    else:
        game.passer_au_tour_suivant(salon)

    return {"juste": False}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
