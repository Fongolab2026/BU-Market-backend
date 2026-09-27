"""Remplit la base avec un jeu de donnees realiste (aucune donnee mock en base).

Usage:
    python manage.py seed_data              # cree les donnees manquantes
    python manage.py seed_data --flush      # supprime le jeu genere puis recree
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from admin.models import PlatformSettings
from categorie.models import Category
from commande.models import Order, OrderItem
from favoris.models import Favorite
from messages.models import Message
from notification.models import Notification
from panier.models import Cart, CartItem
from products.models import Product
from publications.models import PublicationRequest
from shops.models import Boutique

User = get_user_model()

DEMO_PASSWORD = "Demo@2026"

CATEGORIES = [
    ("Électronique", "Téléphones, ordinateurs et accessoires du quotidien."),
    ("Mode", "Vêtements, chaussures et accessoires tendance."),
    ("Alimentaire", "Épicerie, produits frais et boissons."),
    ("Beauté", "Cosmétiques, soins et produits d'hygiène."),
    ("Maison", "Mobilier, décoration et ustensiles."),
    ("Sport", "Équipements et vêtements de sport."),
    ("Librairie", "Livres, cahiers et fournitures scolaires."),
    ("Automobile", "Pièces, accessoires et entretien véhicule."),
]

SELLERS = [
    ("tech", "Aline Uwimana", "Tech Store Bujumbura", "Électronique", "validated", "active", "Gsm, laptops et accessoires garantis."),
    ("mode", "Patrick Ndayizeye", "Mode Africaine", "Mode", "validated", "active", "Pret-a-porter africain et vestes."),
    ("food", "Divine Irakoze", "Saveurs du Burundi", "Alimentaire", "validated", "active", "Epices locales, miel et cafe du Burundi."),
    ("beauty", "Sandrine Mukamana", "Beaute d'Or", "Beauté", "validated", "active", "Soins naturels et cosmetiques importes."),
    ("home", "Eric Nshimirimana", "Habitat & Deco", "Maison", "validated", "active", "Mobilier moderne et decoration interieure."),
    ("sport", "Fabrice Niyondiko", "Sport Express", "Sport", "validated", "active", "Equipements de sport et fitness."),
    ("auto", "Thierry Bizimana", "Auto Pieces BJK", "Automobile", "validated", "active", "Pieces detachees et entretien vehicule."),
    ("librairie", "Grace Nkurunziza", "Librairie du Savoir", "Librairie", "validated", "active", "Livres scolaires, romans et fournitures."),
    ("fitcenter", "Alice Kwizera", "Fit Center Bujumbura", "Sport", "pending", "active", "Salle de sport et coaching."),
    ("garage", "Olivier Nkurunziza", "Garage du Centre", "Automobile", "pending", "active", "Entretien et reconditionnement."),
    ("papeterie", "Josiane Mukandayisenga", "Papeterie Rohero", "Librairie", "suspended", "suspended", "Fournitures de bureau."),
]

AREAS = [
    "Muzinga", "Rohero", "Gatagara", "Nyarutanga", "Kigobe",
    "Buhiga", "Gikongoro", "Buta", "Kiyange", "Rukoni", "Kamenge",
]

BUYERS = [
    ("Aline", "Habimana", "Muzinga"),
    ("Jean", "Bizimana", "Rohero"),
    ("Claudine", "Ndayisaba", "Gatagara"),
    ("Fabrice", "Niyongere", "Kigobe"),
    ("Sandrine", "Ingabire", "Nyarutanga"),
    ("Olivier", "Nkurunziza", "Buta"),
    ("Chantal", "Uwimana", "Kanyosha"),
    ("Bosco", "Niyondiko", "Gikongoro"),
    ("Josiane", "Mukandayisenga", "Buhiga"),
    ("Emmanuel", "Bizimana", "Kamenge"),
]

PRODUCTS = [
    ("Smartphone 128 Go double SIM", 185000, "Électronique", 12, "Android 13, 6,5 pouces, garantie 12 mois."),
    ("Ordinateur portable 8 Go RAM", 620000, "Électronique", 5, "Écran 15,6 pouces, SSD 512 Go, Intel Core i5."),
    ("Casque Bluetooth sport", 35000, "Électronique", 30, "Réduction de bruit, autonomie 20 heures."),
    ("Batterie externe 20 000 mAh", 28000, "Électronique", 45, "Charge rapide 22,5 W, deux ports USB."),
    ("Tissu wax pagne 6 mètres", 45000, "Mode", 25, "Imprimé haute définition, choice de 8 couleurs."),
    ("Chemise homme lin", 32000, "Mode", 18, "Coupe droite, tissu respirant, trois teintes."),
    ("Robe wax fait main", 55000, "Mode", 9, "Sur-mesure, tissu wax burkinabè."),
    ("Sandales cuir tressé", 38000, "Mode", 22, "Cuir véritable, semelle cousue main."),
    ("Miel naturel 1 kg", 22000, "Alimentaire", 60, "Récolte 2026, provenance Kayanza."),
    ("Café du Burundi 250 g", 8500, "Alimentaire", 80, "Torréfaction artisanale, notes fruitées."),
    ("Piment vert séché 100 g", 4000, "Alimentaire", 120, "Fort, idéal pour la cuisine burundaise."),
    ("Farine de manioc 1 kg", 3200, "Alimentaire", 200, "Essentiel pour le kibra et la mak Cobwe."),
    ("Crème hydratante visage", 18000, "Beauté", 40, "Acide hyaluronique, sans parfum, 50 ml."),
    ("Savon noir africain 200 g", 6500, "Beauté", 75, "Nettoyant traditionnel à la cendre de cabosse."),
    ("Huile de coco pressée 250 ml", 9500, "Beauté", 55, "Pure, non raffinée, usage corporel et capillaire."),
    ("Table pliante 6 places", 145000, "Maison", 6, "Chêne massif, finitions Resistant à l'eau."),
    ("Plaid en laine tissée", 48000, "Maison", 14, "Tissage main, 150 x 200 cm."),
    ("Set 6 tasses en céramique", 27000, "Maison", 20, "Émaillage à la main, compatible micro-ondes."),
    ("Tapis berbère 2 x 3 m", 220000, "Maison", 3, "Laine naturelle, motifs traditionnels."),
    ("Ballon de basket cuir", 28000, "Sport", 35, "Taille 7, gomme Grip, usage extérieur."),
    ("Tapis de yoga antidérapant", 19000, "Sport", 28, "6 mm, sans latex,Livré avec sac."),
    ("Gourde isotherme 750 ml", 16000, "Sport", 42, "Acier inoxydable, garde 12 h le froid."),
    ("Roman burundais illustré", 9000, "Librairie", 24, "Roman en Kirundi avec illustrations originales."),
    ("Cahier grand format A4", 3500, "Librairie", 150, "96 pages, papier 80 g, spirale."),
    ("Plaquettes de frein avant", 28000, "Automobile", 16, "Compatible Toyota Corolla 2015-2020."),
    ("Chargeur allume-cigare double", 9000, "Automobile", 65, "Ports USB-A et USB-C, 36 W."),
]

REVIEWS = [
    5, 4, 5, 4, 3, 5, 4, 5, 4, 4, 5, 3, 5, 4, 5, 4, 5, 2,
]

REVIEW_COMMENTS = [
    "Produit conforme à la description, livraison rapide.",
    "Très bon rapport qualité prix, je recommande.",
    "Livraison à Bujumbura en 24 heures, bravo au vendeur.",
    "La qualité du tissu est vraiment au rendez-vous.",
    "Emballage soigné, produit intact à l'arrivée.",
    "Je recommande le vendeur pour un achat serein.",
    "Bonne qualité mais le prix pourrait baisser.",
    "Le vendeur a répondu rapidement à mes questions.",
    "Produit excellent, j'en reprendrai.",
    "Correct pour le prix, sans plus.",
    "Le wax est magnifique, couleurs fidèles.",
    "Très satisfait de ma commande.",
    "Attention, vérifier la taille avant d'acheter.",
    "Produit original, merci pour la qualite.",
]

SHOP_MESSAGES = [
    "Bonjour, le produit est-il toujours disponible ?",
    "Bonjour, oui il reste en stock. Souhaitez-vous commander ?",
    "Bonjour, puis-je avoir une remise si je prends deux ?",
    "Bonjour, je peux faire 5 % de remise pour deux articles.",
    "D'accord, merci. Quelle est la durée de livraison ?",
    "La livraison prend 24 à 48 heures pour Bujumbura.",
    "Parfait, je commande maintenant.",
    "Merci pour votre commande, elle est en préparation.",
    "Bonjour, quel est l'état du produit ?",
    "Bonjour, il est neuf et sous garantie.",
    "Bonjour, faites-vous la livraison vers Gikongoro ?",
    "Oui, nous livrons dans tout Bujumbura pour 3000 BIF.",
    "Très bien, à bientôt.",
    "Merci beaucoup pour votre confiance.",
]


class Command(BaseCommand):
    help = "Remplit la base avec des donnees realistes pour l'espace admin."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Supprime les donnees generees precedemment avant de recreer le jeu.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(2026)
        now = timezone.now()

        if options["flush"]:
            self.stdout.write("Suppression du jeu de donnees precedent...")
            self._flush()

        if Product.objects.filter(name__contains="Smartphone 128 Go").exists() and not options["flush"]:
            self.stdout.write(self.style.WARNING(
                "Le jeu de donnees semble deja present. Utilise --flush pour le recreer."
            ))
            return

        categories = self._create_categories()
        sellers = self._create_sellers(now)
        buyers = self._create_buyers(now)
        products = self._create_products(sellers, categories, now)
        self._create_publications(sellers, products, now)
        self._create_reviews(buyers, products, now)
        self._create_carts(buyers, products)
        self._create_orders(buyers, products, now)
        self._create_messages(sellers, buyers, now)
        self._create_notifications(sellers, buyers, now)
        self._create_boutiques(sellers, now)
        self._create_settings()

        self.stdout.write(self.style.SUCCESS("\nJeu de donnees cree :"))
        self.stdout.write(f"  categories   : {Category.objects.count()}")
        self.stdout.write(f"  utilisateurs : {User.objects.count()}")
        self.stdout.write(f"  boutiques    : {Boutique.objects.count()} (demandes de location)")
        self.stdout.write(f"  produits     : {Product.objects.count()}")
        self.stdout.write(f"  avis         : {Favorite.objects.count()}")
        self.stdout.write(f"  commandes    : {Order.objects.count()}")
        self.stdout.write(f"  messages     : {Message.objects.count()}")
        self.stdout.write(f"  notifications: {Notification.objects.count()}")

    # ------------------------------------------------------------------ utils

    def _flush(self):
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        CartItem.objects.all().delete()
        Cart.objects.all().delete()
        Favorite.objects.all().delete()
        PublicationRequest.objects.all().delete()
        Notification.objects.all().delete()
        Message.objects.all().delete()
        Product.objects.all().delete()
        Boutique.objects.all().delete()
        Category.objects.all().delete()
        User.objects.exclude(username="admin").delete()

    def _ago(self, now, days, hours=0, minutes=0):
        return now - timedelta(days=days, hours=hours, minutes=minutes)

    def _backdate(self, model, pk, field, value):
        model.objects.filter(pk=pk).update(**{field: value})

    # -------------------------------------------------------------- creations

    def _create_categories(self):
        categories = {}
        for name, description in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            if not category.description:
                category.description = description
                category.save(update_fields=["description"])
            categories[name] = category
        self.stdout.write(f"  {len(categories)} categories")
        return categories

    def _create_sellers(self, now):
        areas = [
            "Muzinga", "Rohero", "Gatagara", "Nyarutanga", "Kigobe",
            "Buhiga", "Gikongoro", "Buta", "Kamenge", "Kanyosha", "Rukoni"
        ]
        sellers = []
        for index, (slug, name, shop, category, shop_status, account_status, description) in enumerate(SELLERS):
            first_name, _, last_name = name.partition(" ")
            email = f"{slug}@boutique.bm"
            seller, created = User.objects.get_or_create(
                username=slug,
                defaults={
                    "email": email,
                    "first_name": first_name,
                    "phone": f"+257 7{index + 1} 22 33 {44 + index:02d}",
                    "adresse": f"{areas[index % len(areas)]}, Bujumbura",
                    "role": User.Role.SELLER,
                    "status": account_status,
                    "is_active": account_status != "suspended",
                    "last_active": self._ago(now, index // 3),
                },
            )
            if created:
                self._backdate(User, seller.pk, "date_joined", self._ago(now, 20 - index * 2))
            seller.shop_name = shop
            seller.shop_description = description
            seller.shop_status = shop_status
            seller.shop_views = random.randint(120, 2400)
            seller.shop_category = Category.objects.filter(name=category).first()
            seller.save()
            sellers.append(seller)
        self.stdout.write(f"  {len(sellers)} commercants")
        return sellers

    def _create_buyers(self, now):
        buyers = []
        for index, (first_name, last_name, area) in enumerate(BUYERS):
            username = f"client{index + 1}"
            email = f"{username}@exemple.bm"
            buyer, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": f"{first_name} {last_name}",
                    "phone": f"+257 8{index} 44 55 66",
                    "adresse": f"{area}, Bujumbura",
                    "role": User.Role.BUYER,
                    "status": User.AccountStatus.ACTIVE,
                    "last_active": self._ago(now, 0, index * 3),
                },
            )
            if created:
                self._backdate(User, buyer.pk, "date_joined", self._ago(now, 18 - index))
            buyers.append(buyer)
        self.stdout.write(f"  {len(buyers)} clients")
        return buyers

    def _create_products(self, sellers, categories, now):
        products = []
        validated = [seller for seller in sellers if seller.shop_status == User.ShopStatus.VALIDATED]
        # Un produit est rattache a la boutique qui vend cette categorie.
        by_category = {}
        for seller in validated:
            if seller.shop_category:
                by_category.setdefault(seller.shop_category.name, seller)
        fallback = validated[0]

        for index, (name, price, category_name, stock, details) in enumerate(PRODUCTS):
            seller = by_category.get(category_name, fallback)
            product, created = Product.objects.get_or_create(
                name=name,
                owner=seller,
                defaults={
                    "price": price,
                    "category": categories[category_name],
                    "details": details,
                    "stock": stock,
                    "status": Product.Status.INACTIVE if index % 9 == 4 else Product.Status.ACTIVE,
                    "views": random.randint(15, 900),
                },
            )
            if created:
                product.created_at = self._ago(now, 25 - index, index % 5)
                product.save(update_fields=["created_at"])
            products.append(product)
        self.stdout.write(f"  {len(products)} produits")
        return products

    def _create_publications(self, sellers, products, now):
        requests = []
        statuses = [
            PublicationRequest.Status.PENDING,
            PublicationRequest.Status.PENDING,
            PublicationRequest.Status.PENDING,
            PublicationRequest.Status.APPROVED,
            PublicationRequest.Status.REJECTED,
        ]
        for index, status in enumerate(statuses):
            product = products[index * 4]
            request, created = PublicationRequest.objects.get_or_create(
                product=product,
                seller=product.owner,
                defaults={"status": status},
            )
            if created:
                request.created_at = self._ago(now, 12 - index, index)
                request.save(update_fields=["created_at"])
            requests.append(request)
        self.stdout.write(f"  {len(requests)} demandes de publication")

    def _create_reviews(self, buyers, products, now):
        count = 0
        for index, product in enumerate(products):
            if index % 2 == 1 and len(buyers) < 2:
                continue
            buyer = buyers[index % len(buyers)]
            if Favorite.objects.filter(user=buyer, product=product).exists():
                continue
            stars = REVIEWS[index % len(REVIEWS)]
            favorite = Favorite.objects.create(
                user=buyer,
                product=product,
                stars=stars,
                comment=REVIEW_COMMENTS[index % len(REVIEW_COMMENTS)],
                status=Favorite.Status.HIDDEN if index % 11 == 7 else Favorite.Status.VISIBLE,
            )
            self._backdate(Favorite, favorite.pk, "created_at", self._ago(now, 20 - index, index % 6))
            count += 1
        self.stdout.write(f"  {count} avis")

    def _create_carts(self, buyers, products):
        count = 0
        for index, buyer in enumerate(buyers[:5]):
            cart, _ = Cart.objects.get_or_create(user=buyer)
            if cart.items.exists():
                continue
            for product in products[index : index + 2]:
                CartItem.objects.get_or_create(
                    cart=cart, product=product, defaults={"quantity": random.randint(1, 3)}
                )
            count += 1
        self.stdout.write(f"  {count} paniers")

    def _create_orders(self, buyers, products, now):
        statuses = [
            Order.Status.PENDING,
            Order.Status.PENDING,
            Order.Status.SHIPPED,
            Order.Status.SHIPPED,
            Order.Status.COMPLETED,
            Order.Status.COMPLETED,
            Order.Status.COMPLETED,
            Order.Status.CANCELLED,
            Order.Status.SHIPPED,
            Order.Status.COMPLETED,
            Order.Status.PENDING,
            Order.Status.COMPLETED,
        ]
        count = 0
        for index, status in enumerate(statuses):
            buyer = buyers[index % len(buyers)]
            product = products[index]
            order = Order.objects.create(user=buyer, status=status)
            OrderItem.objects.create(
                order=order, product=product, quantity=random.randint(1, 3), price=product.price
            )
            if index % 4 == 0 and len(products) > index + 1:
                second = products[index + 1]
                OrderItem.objects.create(
                    order=order, product=second, quantity=1, price=second.price
                )
            self._backdate(Order, order.pk, "created_at", self._ago(now, index % 7, 0, (index * 3) % 20))
            count += 1
        self.stdout.write(f"  {count} commandes")

    def _create_messages(self, sellers, buyers, now):
        admin = User.objects.filter(role=User.Role.SUPER_ADMIN).first()
        count = 0
        for index, seller in enumerate(sellers[:5]):
            for turn, content in enumerate(SHOP_MESSAGES):
                buyer = buyers[(index + turn) % len(buyers)]
                if turn % 2 == 0:
                    sender, receiver = buyer, seller
                else:
                    sender, receiver = seller, buyer
                message = Message.objects.create(
                    sender=sender,
                    receiver=receiver,
                    content=content,
                    is_read=turn < 2,
                )
                self._backdate(Message, message.pk, "timestamp", self._ago(now, 0, index * 4 + turn))
                count += 1

        # conversations de l'administrateur avec les Zhiwa (interlocuteurs)
        if admin:
            admin_threads = [
                sellers[0],
                sellers[2],
                sellers[5],
                buyers[0],
            ]
            replies = [
                "Bonjour, pouvez-vous preciser la disponibilite de votre boutique ?",
                "Bonjour, merci de nous transmettre les documents de votre boutique.",
                "Bonjour, votre demande d'espace commercial est en cours d'examen.",
                "Bonjour, votre reclamation a bien ete transmise a l'equipe.",
                "Bonjour, le vendeur vient de repondre a votre question sur le produit.",
                "Bonjour, nous vous remercions pour votre retour sur la commande.",
                "Bonjour, la livraison est confirmee pour demain matin.",
                "Bonjour, votre compte a bien ete reactive.",
            ]
            for index, partner in enumerate(admin_threads):
                for turn in (0, 1, 2):
                    if turn == 2:
                        sender, receiver = partner, admin
                    else:
                        sender, receiver = admin, partner
                    message = Message.objects.create(
                        sender=sender,
                        receiver=receiver,
                        content=replies[(index * 2 + turn) % len(replies)],
                        is_read=turn < 2,
                    )
                    self._backdate(Message, message.pk, "timestamp", self._ago(now, 0, index * 3 + turn))
                    count += 1

        self.stdout.write(f"  {count} messages")

    def _create_notifications(self, sellers, buyers, now):
        templates = [
            ("Nouvelle commande reçue", "Une nouvelle commande a été passée dans votre boutique.", Notification.Type.ORDER),
            ("Produit en attente de validation", "Un commerçant attend la validation de sa boutique.", Notification.Type.SHOP),
            ("Paiement reçu", "Le paiement de la commande a bien été enregistré.", Notification.Type.PRODUCT),
            ("Mise à jour de la plateforme", "Les conditions générales ont été mises à jour.", Notification.Type.SYSTEM),
            ("Offre speciale", "Profitez d'une reduction sur une selection de produits.", Notification.Type.PROMOTION),
            ("Nouveau message", "Vous avez recu un nouveau message.", Notification.Type.MESSAGE),
            ("Alerte de securite", "Une connexion suspecte a ete detectee sur votre compte.", Notification.Type.ALERT),
        ]
        count = 0
        admins = list(User.objects.filter(role__in=[User.Role.SUPER_ADMIN, User.Role.ADMIN]))
        targets = admins + sellers + buyers
        for index, target in enumerate(targets):
            for offset in range(2):
                title, message, kind = templates[(index + offset) % len(templates)]
                notification = Notification.objects.create(
                    user=target,
                    title=title,
                    message=message,
                    type=kind,
                    is_read=offset == 0 and index % 2 == 0,
                )
                self._backdate(
                    Notification, notification.pk, "created_at", self._ago(now, 0, index * 2 + offset * 5)
                )
                count += 1
        self.stdout.write(f"  {count} notifications")

    def _create_boutiques(self, sellers, now):
        requests = [
            ("Sport Express", "Alice Kwizera", "Sport & Fitness", "pending"),
            ("Auto Pieces BJK", "Thierry Bizimana", "Automobile", "pending"),
            ("Librairie du Savoir", "Grace Nkurunziza", "Librairie", "pending"),
            ("Pharmacie Centrale", "Chantal Ndayisaba", "Sante", "validated"),
            ("Cafe du Centre", "Bosco Niyondiko", "Alimentaire", "rejected"),
        ]
        count = 0
        for index, (company, owner, industry, status) in enumerate(requests):
            email = f"contact@{company.split()[0].lower()}.bm"
            request, created = Boutique.objects.get_or_create(
                email=email,
                company_name=company,
                defaults={
                    "owner_name": owner,
                    "industry": industry,
                    "phone": f"+257 7{index} 88 99 00",
                    "whatsapp": f"+257 7{index} 88 99 00",
                    "slogan": f"{company}, votre partenaire de confiance",
                    "province": "Bujumbura Mairie",
                    "commune": ["Rohero", "Muzinga", "Gatagara", "Nyarutanga", "Kigobe"][index],
                    "neighborhood": ["Rukoni", "Bwakamayo", "Kiyange", "Kavumu", "Gihosho"][index],
                    "status": status,
                },
            )
            if created:
                self._backdate(Boutique, request.pk, "created_at", self._ago(now, 15 - index, index))
            count += 1
        self.stdout.write(f"  {count} demandes de location")

    def _create_settings(self):
        PlatformSettings.load()
