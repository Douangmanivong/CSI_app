je fais une appli qt sous python, le projet consiste à recevoir, parser, afficher le spectrogramme de données csi recues via tcp et envoyer un message lorsqu'un certain seuil d'amplitude est dépassé. Le tout se fait en parallèle et en temps réel avec une contrainte de latence la plus faible possible. L'arborescence du projet est la suivante :

main
gui\
     main_window, main_window.ui, plotter
config\
     settings
utils\
     logger 
network\
     tcp_receiver
processing\
     csi_processor

j'ai deja généré un ui dont je peux te fournir le code source. L'objectif est de générer le reste des fichiers, je te detaillerai ce que j'attends de chacun des fichiers, veille a ce qu'il n y ait pas de conflits, que tout soit cohérent et simple (je complexifierai le projet plus tard). 

main_window doit initialiser la fenetre donc ouvrir, charger et appliquer l'ui, il initialise la connexion tcp et la figure pour tracer le spectrogramme.

tcp_receiver permet la connexion tcp, utilise un buffer circulaire pour recevoir les trames csi et permettre le traitement de ces dernieres.

csi_processor utilise lui aussi un buffer circulaire pour recuperer les trames csi, les filtrer, fabriquer le spectrogramme.

plotter recupere le spectrogramme et le trace sur la figure en temps réel.

logger affiche les logs

settings contient l'adresse ip, le port, la taille des buffers qui seront utilisés

j'ai oublié de preciser que csi\_processor faisait la detection de seuil et qu'en cas de depassement, un message devait etre affiché pour la zone status de l'ui pour dire qu'un mouvement a ete detecte. Aussi, je veux une syntaxe de code particuliere (attributs et variables en minuscules suivis de \_m, methodes, classes et fonctions en CamelCase, tout en anglais avec des noms explicites) regenere le code pour que cela corresponde stp

une donnée csi (channel state information) est une matrice contenant amplitude et phase des différents channels du wifi (mon objectif est de faire de la detection de mouvement, en bougeant devant un emetteur et un recepteur wifi, l'amplitude et la phase changent et je veux pouvoir le detecter avec mon appli)
