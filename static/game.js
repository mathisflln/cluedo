document.getElementById("btn-creer").addEventListener("click", async () => {
    const pseudo = document.getElementById("pseudo-creer").value.trim();

    if (pseudo === "") {
        document.getElementById("resultat").textContent = "Écris un pseudo, détective !";
        return;
    }

    const reponse = await fetch("/salon", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pseudo: pseudo })
    });
    const donnees = await reponse.json();
    console.log(donnees);

    if (!reponse.ok) {
        document.getElementById("resultat").textContent = donnees.detail;
        return;
    }

    document.getElementById("resultat").textContent = "Salon créé : " + donnees.code;
    localStorage.setItem("code", donnees.code);
    localStorage.setItem("jeton", donnees.jeton);

    afficherSalle()
});


document.getElementById("btn-rejoindre").addEventListener("click", async () => {
    const code = document.getElementById("code-rejoindre").value.trim().toUpperCase();
    const pseudo = document.getElementById("pseudo-rejoindre").value.trim();

    if (code === "" || pseudo === "") {
        document.getElementById("resultat").textContent = "Tous les champs ne sont pas remplis."
        return;
    }

    const reponse = await fetch(`/salon/${code}/rejoindre`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pseudo: pseudo })
    });
    const donnees = await reponse.json();
    console.log(donnees);

    if (!reponse.ok) {
        document.getElementById("resultat").textContent = donnees.detail;
        return;
    }

    document.getElementById("resultat").textContent = "Tu as rejoint le salon " + code + " avec : " + donnees.joueurs.join(", ");
    localStorage.setItem("code", code);
    localStorage.setItem("jeton", donnees.jeton);

    afficherSalle()
})


async function remplirListe(idListe, elements) {
    const liste = document.getElementById(idListe);
    liste.innerHTML = "";

    for (const joueur of elements) {
        const li = document.createElement("li");
        li.textContent = joueur;
        liste.appendChild(li);
    }
}


function remplirMenu(idMenu, elements) {
    const menu = document.getElementById(idMenu);
    if (menu.options.length > 0) {
        return;
    }
    for (const element of elements) {
        const o = document.createElement("option");
        o.textContent = element;
        menu.appendChild(o);
    }
}


function versTextes(dictionnaire) {
    const textes = [];
    for (const [nom, salle] of Object.entries(dictionnaire)) {
        textes.push(nom + " → " + salle);
    }
    return textes;
}


async function afficherSalle() {
    const code = localStorage.getItem("code");
    if (code === null) {
        document.getElementById("salle").hidden = true;
        document.getElementById("partie").hidden = true;
        document.getElementById("bloc-fin").hidden = true;
        return;
    }

    const reponse = await fetch(`/salon/${code}`);
    const donnees = await reponse.json();

    if (!reponse.ok) {
        localStorage.removeItem("code");
        document.getElementById("salle").hidden = true;
        document.getElementById("partie").hidden = true;
        document.getElementById("bloc-fin").hidden = true;
        return;
    }

    document.getElementById("code-salon").textContent = code;
    remplirListe("liste-joueurs", donnees.joueurs);
    document.getElementById("etat-salon").textContent = donnees.etat;
    document.getElementById("salle").hidden = false;

    const jeton = localStorage.getItem("jeton");

    const repMoi = await fetch(`/salon/${code}/moi?jeton=${jeton}`);
    if (!repMoi.ok) {
        localStorage.removeItem("code");
        localStorage.removeItem("jeton");
        document.getElementById("salle").hidden = true;
        document.getElementById("partie").hidden = true;
        document.getElementById("bloc-fin").hidden = true;
        return;
    }
    const moi = await repMoi.json();

    document.getElementById("btn-lancer").hidden = !moi.hote || donnees.etat !== "attente";

    document.getElementById("bloc-fin").hidden = donnees.etat !== "fini";
    if (donnees.etat !== "lance") {
        document.getElementById("partie").hidden = true;
    }

    if (donnees.etat === "fini") {
        document.getElementById("partie").hidden = true;
        document.getElementById("bloc-fin").hidden = false;

        if (donnees.gagnant !== null) {
            document.getElementById("texte-fin").textContent = donnees.gagnant + " a gagné !";
        } else {
            document.getElementById("texte-fin").textContent = "Tous les détectives ont échoué...";
        }

        const sol = donnees.enveloppe;
        document.getElementById("texte-enveloppe").textContent =
            "La solution : " + sol.suspect + ", avec " + sol.arme + ", dans " + sol.salle + ".";

        remplirListe("journal-final", donnees.journal);
        return;
    }

    if (donnees.etat === "lance") {
        const repMain = await fetch(`/salon/${code}/ma-main?jeton=${jeton}`);
        if (!repMain.ok) {
            return;
        }
        const main = await repMain.json();

        document.getElementById("mon-pseudo").textContent = "Tu es " + moi.pseudo;

        remplirListe("ma-main", main.cartes);
        remplirListe("cartes-visibles", donnees.visibles);
        document.getElementById("visible").hidden = donnees.visibles.length === 0;

        remplirListe("pos-joueurs", versTextes(donnees.positions_joueurs));
        remplirListe("pos-suspects", versTextes(donnees.positions_suspects));
        remplirListe("pos-armes", versTextes(donnees.positions_armes));

        if (donnees.joueur_actif === moi.pseudo) {
            document.getElementById("info-tour").textContent = "C'est ton tour ! - " + donnees.pa + " PA";
        } else {
            document.getElementById("info-tour").textContent = "Tour de " + donnees.joueur_actif + " - " + donnees.pa + " PA";
        }

        if (donnees.elimines.includes(moi.pseudo)) {
            document.getElementById("info-tour").textContent = "Tu es éliminé, mais tu peux encore répondre aux suppositions.";
        }

        remplirListe("journal", donnees.journal);

        if (donnees.attend !== null) {
            document.getElementById("attente").textContent = "En attente de la réponse de " + donnees.attend + "...";
        } else {
            document.getElementById("attente").textContent = "";
        }

        const repOptions = await fetch(`/salon/${code}/options?jeton=${jeton}`);
        if (!repOptions.ok) {
            return;
        }
        const opt = await repOptions.json();

        const div = document.getElementById("options");
        div.innerHTML = "";

        for (const option of opt.options) {
            const b = document.createElement("button");
            b.textContent = option.salle + " (" + option.cout + " PA)";
            b.addEventListener("click", async () => {
                const repDep = await fetch(`/salon/${code}/deplacer?jeton=${jeton}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ destination: option.salle })
                });
                const resDep = await repDep.json();

                if (!repDep.ok) {
                    document.getElementById("resultat").textContent = resDep.detail;
                    return;
                }

                afficherSalle();
            });
            div.appendChild(b);
        }

        document.getElementById("btn-finir").hidden = opt.options.length === 0;

        remplirMenu("choix-suspect", donnees.suspects);
        remplirMenu("choix-arme", donnees.armes);
        remplirMenu("acc-suspect", donnees.suspects);
        remplirMenu("acc-arme", donnees.armes);
        remplirMenu("acc-salle", donnees.salles);
        document.getElementById("bloc-supposition").hidden = !opt.peut_supposer;
        document.getElementById("bloc-accusation").hidden = !opt.peut_accuser;

        const repSupp = await fetch(`/salon/${code}/supposition?jeton=${jeton}`);
        if (repSupp.ok) {
            const supp = await repSupp.json();

            if (!supp.a_repondre) {
                document.getElementById("bloc-repondre").hidden = true;
            } else {
                document.getElementById("texte-supposition").textContent =
                    supp.auteur + " suppose : " + supp.suspect + " avec " + supp.arme + ", dans " + supp.salle + ". Quelle carte montres-tu ?";

                const divCartes = document.getElementById("choix-cartes");
                divCartes.innerHTML = "";

                for (const carte of supp.cartes) {
                    const bc = document.createElement("button");
                    bc.textContent = carte;
                    bc.addEventListener("click", async () => {
                        const repRep = await fetch(`/salon/${code}/repondre?jeton=${jeton}`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ carte: carte })
                        });
                        const resRep = await repRep.json();

                        if (!repRep.ok) {
                            document.getElementById("resultat").textContent = resRep.detail;
                            return;
                        }

                        afficherSalle();
                    });
                    divCartes.appendChild(bc);
                }

                document.getElementById("bloc-repondre").hidden = false;
            }
        }

        const repRecue = await fetch(`/salon/${code}/ma-reponse?jeton=${jeton}`);
        if (repRecue.ok) {
            const recue = await repRecue.json();
            const p = document.getElementById("ma-reponse");

            if (recue.reponse === null) {
                p.textContent = "";
            } else if (recue.reponse.repondant === null) {
                p.textContent = "Personne n'a pu te contredire.";
            } else {
                p.textContent = recue.reponse.repondant + " t'a montré : " + recue.reponse.carte;
            }
        }

        document.getElementById("partie").hidden = false;
    }
}


afficherSalle();

setInterval(afficherSalle, 2000);

document.getElementById("btn-lancer").addEventListener("click", async () => {
    const code = localStorage.getItem("code");
    const jeton = localStorage.getItem("jeton");

    const reponse = await fetch(`/salon/${code}/lancer?jeton=${jeton}`, {
        method: "POST"
    });

    const donnees = await reponse.json();

    if (!reponse.ok) {
        document.getElementById("resultat").textContent = donnees.detail;
        return;
    }

    afficherSalle();
})


document.getElementById("btn-finir").addEventListener("click", async () => {
    const code = localStorage.getItem("code");
    const jeton = localStorage.getItem("jeton");

    const reponse = await fetch(`/salon/${code}/finir-tour?jeton=${jeton}`, {
        method: "POST"
    });

    const donnees = await reponse.json();

    if (!reponse.ok) {
        document.getElementById("resultat").textContent = donnees.detail;
        return;
    }

    afficherSalle();
});


document.getElementById("btn-supposer").addEventListener("click", async () => {
    const code = localStorage.getItem("code");
    const jeton = localStorage.getItem("jeton");
    const suspect = document.getElementById("choix-suspect").value;
    const arme = document.getElementById("choix-arme").value;

    const reponse = await fetch(`/salon/${code}/supposer?jeton=${jeton}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ suspect: suspect, arme: arme })
    });
    const donnees = await reponse.json();

    if (!reponse.ok) {
        document.getElementById("resultat").textContent = donnees.detail;
        return;
    }

    afficherSalle();
});


document.getElementById("btn-accuser").addEventListener("click", async () => {
    const code = localStorage.getItem("code");
    const jeton = localStorage.getItem("jeton");
    const suspect = document.getElementById("acc-suspect").value;
    const arme = document.getElementById("acc-arme").value;
    const salle = document.getElementById("acc-salle").value;

    const reponse = await fetch(`/salon/${code}/accuser?jeton=${jeton}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ suspect: suspect, arme: arme, salle: salle })
    });
    const donnees = await reponse.json();

    if (!reponse.ok) {
        document.getElementById("resultat").textContent = donnees.detail;
        return;
    }

    if (donnees.juste) {
        document.getElementById("resultat").textContent = "Bravo !";
    } else {
        document.getElementById("resultat").textContent = "Fausse accusation, tu es éliminé.";
    }

    afficherSalle();
});

document.getElementById("btn-quitter").addEventListener("click", () => {
    localStorage.removeItem("code");
    localStorage.removeItem("jeton");
    document.getElementById("resultat").textContent = "";
    afficherSalle();
});