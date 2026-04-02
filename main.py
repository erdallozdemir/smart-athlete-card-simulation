import sys
import csv
import random
from abc import ABC, abstractmethod

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QListWidget,
    QTextEdit, QVBoxLayout, QHBoxLayout, QGridLayout, QMessageBox,
    QFileDialog, QComboBox, QListWidgetItem, QFrame, QProgressBar
)
from PyQt5.QtCore import Qt


# =========================================================
# ÖZEL YETENEKLER
# =========================================================

class OzelYetenek(ABC):
    def __init__(self, ad):
        self.ad = ad

    @abstractmethod
    def bonus_hesapla(self, kart, oyun_durumu):
        pass

    def enerji_carpani(self):
        return 1.0

    def rakip_bonusunu_etkile(self, bonus):
        return bonus

    def aciklama(self):
        return self.ad


class ClutchPlayer(OzelYetenek):
    def __init__(self):
        super().__init__("Clutch Player")

    def bonus_hesapla(self, kart, oyun_durumu):
        kalan_tur = oyun_durumu["toplam_tur"] - oyun_durumu["mevcut_tur"] + 1
        return 10 if kalan_tur <= 3 else 0


class Captain(OzelYetenek):
    def __init__(self):
        super().__init__("Captain")

    def bonus_hesapla(self, kart, oyun_durumu):
        return 5


class Legend(OzelYetenek):
    def __init__(self):
        super().__init__("Legend")
        self.kullanildi = False

    def bonus_hesapla(self, kart, oyun_durumu):
        if not self.kullanildi:
            self.kullanildi = True
            return 15
        return 0


class Defender(OzelYetenek):
    def __init__(self):
        super().__init__("Defender")

    def bonus_hesapla(self, kart, oyun_durumu):
        return 0

    def rakip_bonusunu_etkile(self, bonus):
        return bonus / 2


class Veteran(OzelYetenek):
    def __init__(self):
        super().__init__("Veteran")

    def bonus_hesapla(self, kart, oyun_durumu):
        return 0

    def enerji_carpani(self):
        return 0.5


class Finisher(OzelYetenek):
    def __init__(self):
        super().__init__("Finisher")

    def bonus_hesapla(self, kart, oyun_durumu):
        return 8 if kart.enerji < 40 else 0


def ozel_yetenek_olustur(ad):
    ad = ad.strip().lower()
    if ad == "clutch player":
        return ClutchPlayer()
    elif ad == "captain":
        return Captain()
    elif ad == "legend":
        return Legend()
    elif ad == "defender":
        return Defender()
    elif ad == "veteran":
        return Veteran()
    elif ad == "finisher":
        return Finisher()
    return Captain()


# =========================================================
# SPORCU KARTLARI
# =========================================================

class Sporcu(ABC):
    next_id = 1

    def __init__(self, sporcu_adi, takim_adi, enerji, dayaniklilik, ozel_yetenek):
        self.sporcuID = Sporcu.next_id
        Sporcu.next_id += 1

        self.sporcuAdi = sporcu_adi
        self.sporcuTakim = takim_adi
        self.enerji = int(enerji)
        self.maxEnerji = int(enerji)
        self.seviye = 1
        self.deneyimPuani = 0
        self.kartKullanildiMi = False
        self.ozelYetenek = ozel_yetenek
        self.dayaniklilik = int(dayaniklilik)

        self.kullanimSayisi = 0
        self.kazanmaSayisi = 0
        self.kaybetmeSayisi = 0

    @abstractmethod
    def branş(self):
        pass

    @abstractmethod
    def ozellikler(self):
        pass

    def kartBilgisiYazdir(self):
        oz = ", ".join([f"{k}:{v}" for k, v in self.ozellikler().items()])
        return (
            f"ID:{self.sporcuID} | {self.sporcuAdi} | {self.sporcuTakim} | {self.branş()} | "
            f"Enerji:{self.enerji}/{self.maxEnerji} | Seviye:{self.seviye} | "
            f"XP:{self.deneyimPuani} | Day:{self.dayaniklilik} | "
            f"Yetenek:{self.ozelYetenek.ad} | {oz}"
        )

    def moral_bonusu_hesapla(self, oyuncu_morali):
        if oyuncu_morali >= 80:
            return 10
        elif oyuncu_morali >= 50:
            return 5
        return -5

    def seviye_bonusu_hesapla(self):
        if self.seviye == 1:
            return 0
        elif self.seviye == 2:
            return 5
        return 10

    def enerji_cezasi_hesapla(self, temel_ozellik):
        if self.enerji > 70:
            return 0
        elif 40 <= self.enerji <= 70:
            return temel_ozellik * 0.10
        elif 0 < self.enerji < 40:
            return temel_ozellik * 0.20
        return 999999

    def performansHesapla(self, ozellik_adi, oyuncu_morali, oyun_durumu):
        if self.enerji <= 0:
            return -999999

        temel = self.ozellikler()[ozellik_adi]
        moral_bonus = self.moral_bonusu_hesapla(oyuncu_morali)
        ozel_bonus = self.ozelYetenek.bonus_hesapla(self, oyun_durumu)
        seviye_bonus = self.seviye_bonusu_hesapla()
        enerji_cezasi = self.enerji_cezasi_hesapla(temel)

        return temel + moral_bonus + ozel_bonus - enerji_cezasi + seviye_bonus

    def enerjiGuncelle(self, durum, ozel_yetenek_kullanildi=False):
        if durum == "kazandi":
            dusus = 5
        elif durum == "kaybetti":
            dusus = 10
        else:
            dusus = 3

        if ozel_yetenek_kullanildi:
            dusus += 5

        dusus *= self.ozelYetenek.enerji_carpani()
        self.enerji = max(0, int(self.enerji - dusus))

    def seviyeAtlaKontrol(self):
        yeni_seviye = self.seviye
        if self.kazanmaSayisi >= 4 or self.deneyimPuani >= 8:
            yeni_seviye = 3
        elif self.kazanmaSayisi >= 2 or self.deneyimPuani >= 4:
            yeni_seviye = 2

        if yeni_seviye > self.seviye:
            fark = yeni_seviye - self.seviye
            self.seviye = yeni_seviye
            self.maxEnerji += 10 * fark
            self.enerji = min(self.maxEnerji, self.enerji + 10 * fark)
            self.dayaniklilik += 5 * fark
            self.seviye_artis_ozellikleri(5 * fark)
            return True
        return False

    @abstractmethod
    def seviye_artis_ozellikleri(self, artis):
        pass


class Futbolcu(Sporcu):
    def __init__(self, sporcu_adi, takim_adi, penalti, serbestVurus, kaleciKarsiKarsiya,
                 dayaniklilik, enerji, ozel_yetenek):
        super().__init__(sporcu_adi, takim_adi, enerji, dayaniklilik, ozel_yetenek)
        self.penalti = int(penalti)
        self.serbestVurus = int(serbestVurus)
        self.kaleciKarsiKarsiya = int(kaleciKarsiKarsiya)

    def branş(self):
        return "Futbol"

    def ozellikler(self):
        return {
            "Penalti": self.penalti,
            "SerbestVurus": self.serbestVurus,
            "KaleciKarsiKarsiya": self.kaleciKarsiKarsiya
        }

    def seviye_artis_ozellikleri(self, artis):
        self.penalti += artis
        self.serbestVurus += artis
        self.kaleciKarsiKarsiya += artis


class Basketbolcu(Sporcu):
    def __init__(self, sporcu_adi, takim_adi, ucluk, ikilik, serbestAtis,
                 dayaniklilik, enerji, ozel_yetenek):
        super().__init__(sporcu_adi, takim_adi, enerji, dayaniklilik, ozel_yetenek)
        self.ucluk = int(ucluk)
        self.ikilik = int(ikilik)
        self.serbestAtis = int(serbestAtis)

    def branş(self):
        return "Basketbol"

    def ozellikler(self):
        return {
            "Ucluk": self.ucluk,
            "Ikilik": self.ikilik,
            "SerbestAtis": self.serbestAtis
        }

    def seviye_artis_ozellikleri(self, artis):
        self.ucluk += artis
        self.ikilik += artis
        self.serbestAtis += artis


class Voleybolcu(Sporcu):
    def __init__(self, sporcu_adi, takim_adi, servis, blok, smac,
                 dayaniklilik, enerji, ozel_yetenek):
        super().__init__(sporcu_adi, takim_adi, enerji, dayaniklilik, ozel_yetenek)
        self.servis = int(servis)
        self.blok = int(blok)
        self.smac = int(smac)

    def branş(self):
        return "Voleybol"

    def ozellikler(self):
        return {
            "Servis": self.servis,
            "Blok": self.blok,
            "Smac": self.smac
        }

    def seviye_artis_ozellikleri(self, artis):
        self.servis += artis
        self.blok += artis
        self.smac += artis


# =========================================================
# OYUNCULAR
# =========================================================

class Oyuncu(ABC):
    next_id = 1

    def __init__(self, oyuncuAdi):
        self.oyuncuID = Oyuncu.next_id
        Oyuncu.next_id += 1
        self.oyuncuAdi = oyuncuAdi
        self.skor = 0
        self.moral = 60
        self.kartListesi = []
        self.galibiyetSerisi = 0
        self.kaybetmeSerisi = 0
        self.toplamGalibiyet = 0
        self.toplamBeraberlik = 0
        self.ozelYetenekliGalibiyet = 0
        self.galibiyetSerisiSayisi = 0

    def uygun_kartlar(self, branş):
        return [k for k in self.kartListesi if k.branş() == branş and k.enerji > 0]

    @abstractmethod
    def kartSec(self, branş, oyun_durumu=None):
        pass


class Kullanici(Oyuncu):
    def __init__(self, oyuncuAdi):
        super().__init__(oyuncuAdi)

    def kartSec(self, branş, oyun_durumu=None):
        return self.uygun_kartlar(branş)


class Bilgisayar(Oyuncu):
    def __init__(self, oyuncuAdi, strateji):
        super().__init__(oyuncuAdi)
        self.strateji = strateji

    def kartSec(self, branş, oyun_durumu=None):
        uygunlar = self.uygun_kartlar(branş)
        return self.strateji.kartSec(uygunlar, oyun_durumu)


# =========================================================
# STRATEJI
# =========================================================

class KartSecmeStratejisi(ABC):
    @abstractmethod
    def kartSec(self, kartlar, oyun_durumu):
        pass


class KolayStrateji(KartSecmeStratejisi):
    def kartSec(self, kartlar, oyun_durumu):
        if not kartlar:
            return None
        return random.choice(kartlar)


class OrtaStrateji(KartSecmeStratejisi):
    def kartSec(self, kartlar, oyun_durumu):
        if not kartlar:
            return None

        oyuncu_morali = oyun_durumu["bilgisayar_morali"]
        ozellikler = list(kartlar[0].ozellikler().keys())

        en_iyi = None
        en_iyi_skor = -999999

        for kart in kartlar:
            ort = 0
            for oz in ozellikler:
                ort += kart.performansHesapla(oz, oyuncu_morali, oyun_durumu)
            ort /= len(ozellikler)

            if ort > en_iyi_skor:
                en_iyi_skor = ort
                en_iyi = kart

        return en_iyi


# =========================================================
# İSTATİSTİK
# =========================================================

class MacIstatistik:
    def __init__(self):
        self.tur_gecmisi = []

    def tur_ekle(self, veri):
        self.tur_gecmisi.append(veri)

    def rapor_olustur(self):
        metin = ["--- MAÇ İSTATİSTİK RAPORU ---"]
        for t in self.tur_gecmisi:
            metin.append(
                f"Tur {t['tur_no']} | Branş:{t['branş']} | Özellik:{t['ozellik']} | "
                f"Kullanıcı:{t['kullanici_kart']} ({t['kullanici_puan']:.1f}) | "
                f"Bilgisayar:{t['bilgisayar_kart']} ({t['bilgisayar_puan']:.1f}) | "
                f"Sonuç:{t['sonuc']}"
            )
        return "\n".join(metin)


# =========================================================
# DOSYA OKUYUCU
# =========================================================

class VeriOkuyucu:
    @staticmethod
    def dosyadan_oku(dosya_yolu):
        kartlar = []
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for satir in reader:
                tur = satir["tur"].strip().lower()
                ad = satir["ad"]
                takim = satir["takim"]
                day = satir["dayaniklilik"]
                enerji = satir["enerji"]
                yetenek = ozel_yetenek_olustur(satir["ozel_yetenek"])

                if tur == "futbol":
                    kart = Futbolcu(ad, takim, satir["oz1"], satir["oz2"], satir["oz3"], day, enerji, yetenek)
                elif tur == "basketbol":
                    kart = Basketbolcu(ad, takim, satir["oz1"], satir["oz2"], satir["oz3"], day, enerji, yetenek)
                elif tur == "voleybol":
                    kart = Voleybolcu(ad, takim, satir["oz1"], satir["oz2"], satir["oz3"], day, enerji, yetenek)
                else:
                    raise ValueError(f"Geçersiz tür bulundu: {tur}")

                kartlar.append(kart)

        return kartlar


# =========================================================
# KART WIDGET
# =========================================================

class KartWidget(QFrame):
    def __init__(self, kart, sonuc=None):
        super().__init__()
        self.kart = kart
        self.sonuc = sonuc  # "kazandi", "kaybetti", "berabere", None

        self.setObjectName("kartFrame")
        self.setMinimumHeight(190)
        self.setFrameShape(QFrame.StyledPanel)

        self.arayuzu_kur()
        self.stil_uygula()

    def brans_rengi(self):
        if self.kart.branş() == "Futbol":
            return "#dff5e3"
        elif self.kart.branş() == "Basketbol":
            return "#fff0d9"
        return "#dfefff"

    def sonuc_rengi(self):
        if self.sonuc == "kazandi":
            return "#c8f7c5"
        elif self.sonuc == "kaybetti":
            return "#ffe699"
        elif self.sonuc == "berabere":
            return "#d9edf7"
        return self.brans_rengi()

    def arayuzu_kur(self):
        ana = QVBoxLayout()
        ana.setContentsMargins(10, 8, 10, 8)
        ana.setSpacing(6)

        ust = QHBoxLayout()

        lblAd = QLabel(self.kart.sporcuAdi)
        lblAd.setStyleSheet("font-size:16px; font-weight:bold;")

        lblBrans = QLabel(self.kart.branş())
        lblBrans.setStyleSheet("""
            background-color: rgba(0,0,0,0.08);
            padding: 4px 8px;
            border-radius: 8px;
            font-weight: bold;
        """)

        ust.addWidget(lblAd)
        ust.addStretch()
        ust.addWidget(lblBrans)

        lblTakim = QLabel(f"Takım: {self.kart.sporcuTakim}")
        lblTakim.setStyleSheet("font-size:12px; color:#333;")

        bilgiler = QGridLayout()
        bilgiler.addWidget(QLabel(f"ID: {self.kart.sporcuID}"), 0, 0)
        bilgiler.addWidget(QLabel(f"Seviye: {self.kart.seviye}"), 0, 1)
        bilgiler.addWidget(QLabel(f"XP: {self.kart.deneyimPuani}"), 0, 2)
        bilgiler.addWidget(QLabel(f"Dayanıklılık: {self.kart.dayaniklilik}"), 1, 0)
        bilgiler.addWidget(QLabel(f"Yetenek: {self.kart.ozelYetenek.ad}"), 1, 1, 1, 2)

        enerjiYazi = QLabel(f"Enerji: {self.kart.enerji}/{self.kart.maxEnerji}")

        self.enerjiBar = QProgressBar()
        self.enerjiBar.setMaximum(self.kart.maxEnerji)
        self.enerjiBar.setValue(self.kart.enerji)
        self.enerjiBar.setTextVisible(False)
        self.enerjiBar.setFixedHeight(12)

        if self.kart.enerji < 20:
            bar_renk = "#e53935"
        elif self.kart.enerji < 50:
            bar_renk = "#f9a825"
        else:
            bar_renk = "#43a047"

        self.enerjiBar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #999;
                border-radius: 6px;
                background: #f3f3f3;
            }}
            QProgressBar::chunk {{
                background-color: {bar_renk};
                border-radius: 6px;
            }}
        """)

        ozellikKutusu = QHBoxLayout()
        for ad, deger in self.kart.ozellikler().items():
            lbl = QLabel(f"{ad}: {deger}")
            lbl.setStyleSheet("""
                background:#ffffffcc;
                border:1px solid #aaa;
                border-radius:8px;
                padding:4px 8px;
                font-size:11px;
            """)
            ozellikKutusu.addWidget(lbl)

        ana.addLayout(ust)
        ana.addWidget(lblTakim)
        ana.addLayout(bilgiler)
        ana.addWidget(enerjiYazi)
        ana.addWidget(self.enerjiBar)
        ana.addLayout(ozellikKutusu)

        self.setLayout(ana)

    def stil_uygula(self):
        self.setStyleSheet(f"""
            QFrame#kartFrame {{
                background-color: {self.sonuc_rengi()};
                border: 2px solid #8a8a8a;
                border-radius: 14px;
            }}
        """)


# =========================================================
# OYUN YÖNETİCİ
# =========================================================

class OyunYonetici:
    def __init__(self, kartlar, strateji):
        self.kullanici = Kullanici("Kullanıcı")
        self.bilgisayar = Bilgisayar("Bilgisayar", strateji)
        self.istatistik = MacIstatistik()

        self.turSirasi = ["Futbol", "Basketbol", "Voleybol"] * 8
        self.mevcutTur = 1
        self.toplamTur = len(self.turSirasi)
        self.deste = kartlar

        self.son_bilgisayar_karti_id = None
        self.son_kullanici_karti_id = None
        self.son_kazanan = None

        self.kartlari_dagit()

    def kartlari_dagit(self):
        futbol = [k for k in self.deste if k.branş() == "Futbol"]
        basket = [k for k in self.deste if k.branş() == "Basketbol"]
        voley = [k for k in self.deste if k.branş() == "Voleybol"]

        random.shuffle(futbol)
        random.shuffle(basket)
        random.shuffle(voley)

        self.kullanici.kartListesi = futbol[:4] + basket[:4] + voley[:4]
        self.bilgisayar.kartListesi = futbol[4:] + basket[4:] + voley[4:]

        random.shuffle(self.kullanici.kartListesi)
        random.shuffle(self.bilgisayar.kartListesi)

    def mevcut_branş(self):
        if self.mevcutTur > self.toplamTur:
            return None
        return self.turSirasi[self.mevcutTur - 1]

    def oyun_durumu(self):
        return {
            "mevcut_tur": self.mevcutTur,
            "toplam_tur": self.toplamTur,
            "kullanici_morali": self.kullanici.moral,
            "bilgisayar_morali": self.bilgisayar.moral
        }

    def rastgele_ozellik_sec(self, kart):
        return random.choice(list(kart.ozellikler().keys()))

    def kart_uygun_mu(self, kart, branş):
        return kart is not None and kart.branş() == branş and kart.enerji > 0

    def moral_guncelle(self, kazanan, kaybeden, berabere=False):
        if berabere:
            return

        kazanan.galibiyetSerisi += 1
        kazanan.kaybetmeSerisi = 0
        kaybeden.kaybetmeSerisi += 1
        kaybeden.galibiyetSerisi = 0

        if kazanan.galibiyetSerisi == 2:
            kazanan.moral = min(100, kazanan.moral + 10)
        elif kazanan.galibiyetSerisi >= 3:
            kazanan.moral = min(100, kazanan.moral + 15)

        if kaybeden.kaybetmeSerisi >= 2:
            kaybeden.moral = max(0, kaybeden.moral - 10)

    def seri_bonus_hesapla(self, oyuncu):
        bonus = 0
        if oyuncu.galibiyetSerisi == 3:
            bonus += 10
            oyuncu.galibiyetSerisiSayisi += 1
        elif oyuncu.galibiyetSerisi == 5:
            bonus += 20
            oyuncu.galibiyetSerisiSayisi += 1
        return bonus

    def tur_kazanani_belirle(self, kk, bk, ozellik):
        durum = self.oyun_durumu()

        k_puan = kk.performansHesapla(ozellik, self.kullanici.moral, durum)
        b_puan = bk.performansHesapla(ozellik, self.bilgisayar.moral, durum)

        k_bonus = kk.ozelYetenek.bonus_hesapla(kk, durum)
        b_bonus = bk.ozelYetenek.bonus_hesapla(bk, durum)

        k_bonus = bk.ozelYetenek.rakip_bonusunu_etkile(k_bonus)
        b_bonus = kk.ozelYetenek.rakip_bonusunu_etkile(b_bonus)

        k_puan += k_bonus
        b_puan += b_bonus

        if k_puan > b_puan:
            return "kullanici", k_puan, b_puan, k_bonus > 0
        elif b_puan > k_puan:
            return "bilgisayar", k_puan, b_puan, b_bonus > 0

        digerleri = [x for x in kk.ozellikler().keys() if x != ozellik]
        for d in digerleri:
            kp = kk.performansHesapla(d, self.kullanici.moral, durum)
            bp = bk.performansHesapla(d, self.bilgisayar.moral, durum)
            if kp > bp:
                return "kullanici", k_puan, b_puan, k_bonus > 0
            elif bp > kp:
                return "bilgisayar", k_puan, b_puan, b_bonus > 0

        if kk.dayaniklilik > bk.dayaniklilik:
            return "kullanici", k_puan, b_puan, k_bonus > 0
        elif bk.dayaniklilik > kk.dayaniklilik:
            return "bilgisayar", k_puan, b_puan, b_bonus > 0

        if kk.enerji > bk.enerji:
            return "kullanici", k_puan, b_puan, k_bonus > 0
        elif bk.enerji > kk.enerji:
            return "bilgisayar", k_puan, b_puan, b_bonus > 0

        if kk.seviye > bk.seviye:
            return "kullanici", k_puan, b_puan, k_bonus > 0
        elif bk.seviye > kk.seviye:
            return "bilgisayar", k_puan, b_puan, b_bonus > 0

        return "berabere", k_puan, b_puan, False

    def puan_ver(self, sonuc, ozel_etkili=False, hukmen=False, kart=None, oyuncu=None):
        if sonuc == "berabere":
            return 0

        puan = 8 if hukmen else 10
        if ozel_etkili:
            puan = 15

        if kart and kart.enerji < 30:
            puan += 5

        if oyuncu:
            puan += self.seri_bonus_hesapla(oyuncu)

        return puan

    def tur_oyna(self, kullanici_karti, secilen_ozellik=None):
        branş = self.mevcut_branş()
        if branş is None:
            return {"bitti": True, "mesaj": "Oyun bitti."}

        uygun_k = self.kullanici.uygun_kartlar(branş)
        uygun_b = self.bilgisayar.uygun_kartlar(branş)

        self.son_bilgisayar_karti_id = None
        self.son_kullanici_karti_id = None
        self.son_kazanan = None

        if not uygun_k and not uygun_b:
            self.mevcutTur += 1
            return {"bitti": False, "mesaj": f"{branş} turu atlandı. İki tarafta da uygun kart yok."}

        if not uygun_k and uygun_b:
            bkart = self.bilgisayar.kartSec(branş, self.oyun_durumu())
            self.son_bilgisayar_karti_id = bkart.sporcuID if bkart else None
            self.son_kazanan = "bilgisayar"

            puan = self.puan_ver("bilgisayar", hukmen=True, oyuncu=self.bilgisayar)
            self.bilgisayar.skor += puan
            self.moral_guncelle(self.bilgisayar, self.kullanici)
            self.mevcutTur += 1
            return {"bitti": False, "mesaj": f"{branş} turu hükmen bilgisayar kazandı. +{puan} puan"}

        if uygun_k and not uygun_b:
            self.son_kullanici_karti_id = kullanici_karti.sporcuID if kullanici_karti else None
            self.son_kazanan = "kullanici"

            puan = self.puan_ver("kullanici", hukmen=True, oyuncu=self.kullanici)
            self.kullanici.skor += puan
            self.moral_guncelle(self.kullanici, self.bilgisayar)
            self.mevcutTur += 1
            return {"bitti": False, "mesaj": f"{branş} turu hükmen kullanıcı kazandı. +{puan} puan"}

        if not self.kart_uygun_mu(kullanici_karti, branş):
            return {"bitti": False, "mesaj": f"Hatalı seçim. Bu tur için branş: {branş}"}

        bilgisayar_karti = self.bilgisayar.kartSec(branş, self.oyun_durumu())
        self.son_kullanici_karti_id = kullanici_karti.sporcuID
        self.son_bilgisayar_karti_id = bilgisayar_karti.sporcuID if bilgisayar_karti else None

        if secilen_ozellik:
            ozellik = secilen_ozellik
        else:
            ozellik = self.rastgele_ozellik_sec(kullanici_karti)

        sonuc, kp, bp, ozel_etkili = self.tur_kazanani_belirle(
            kullanici_karti, bilgisayar_karti, ozellik
        )

        if sonuc == "kullanici":
            self.son_kazanan = "kullanici"

            kullanici_karti.kazanmaSayisi += 1
            kullanici_karti.deneyimPuani += 2
            bilgisayar_karti.kaybetmeSayisi += 1

            kullanici_karti.enerjiGuncelle("kazandi", ozel_etkili)
            bilgisayar_karti.enerjiGuncelle("kaybetti")

            puan = self.puan_ver("kullanici", ozel_etkili, False, kullanici_karti, self.kullanici)
            self.kullanici.skor += puan
            self.kullanici.toplamGalibiyet += 1
            if ozel_etkili:
                self.kullanici.ozelYetenekliGalibiyet += 1
            self.moral_guncelle(self.kullanici, self.bilgisayar)
            seviye_atladi = kullanici_karti.seviyeAtlaKontrol()

            mesaj = (
                f"TUR {self.mevcutTur} | {branş}\n"
                f"Özellik: {ozellik}\n"
                f"{kullanici_karti.sporcuAdi}: {kp:.1f}\n"
                f"{bilgisayar_karti.sporcuAdi}: {bp:.1f}\n"
                f"Kazanan: Kullanıcı (+{puan} puan)"
            )
            if seviye_atladi:
                self.kullanici.skor += 5
                mesaj += "\nSeviye atlandı! Ek +5 puan"

        elif sonuc == "bilgisayar":
            self.son_kazanan = "bilgisayar"

            bilgisayar_karti.kazanmaSayisi += 1
            bilgisayar_karti.deneyimPuani += 2
            kullanici_karti.kaybetmeSayisi += 1

            bilgisayar_karti.enerjiGuncelle("kazandi", ozel_etkili)
            kullanici_karti.enerjiGuncelle("kaybetti")

            puan = self.puan_ver("bilgisayar", ozel_etkili, False, bilgisayar_karti, self.bilgisayar)
            self.bilgisayar.skor += puan
            self.bilgisayar.toplamGalibiyet += 1
            if ozel_etkili:
                self.bilgisayar.ozelYetenekliGalibiyet += 1
            self.moral_guncelle(self.bilgisayar, self.kullanici)
            bilgisayar_karti.seviyeAtlaKontrol()

            mesaj = (
                f"TUR {self.mevcutTur} | {branş}\n"
                f"Özellik: {ozellik}\n"
                f"{kullanici_karti.sporcuAdi}: {kp:.1f}\n"
                f"{bilgisayar_karti.sporcuAdi}: {bp:.1f}\n"
                f"Kazanan: Bilgisayar (+{puan} puan)"
            )

        else:
            self.son_kazanan = "berabere"

            self.kullanici.toplamBeraberlik += 1
            self.bilgisayar.toplamBeraberlik += 1

            kullanici_karti.deneyimPuani += 1
            bilgisayar_karti.deneyimPuani += 1

            kullanici_karti.enerjiGuncelle("berabere")
            bilgisayar_karti.enerjiGuncelle("berabere")

            kullanici_karti.seviyeAtlaKontrol()
            bilgisayar_karti.seviyeAtlaKontrol()

            mesaj = (
                f"TUR {self.mevcutTur} | {branş}\n"
                f"Özellik: {ozellik}\n"
                f"{kullanici_karti.sporcuAdi}: {kp:.1f}\n"
                f"{bilgisayar_karti.sporcuAdi}: {bp:.1f}\n"
                f"Sonuç: Berabere"
            )

        self.istatistik.tur_ekle({
            "tur_no": self.mevcutTur,
            "branş": branş,
            "ozellik": ozellik,
            "kullanici_kart": kullanici_karti.sporcuAdi,
            "bilgisayar_kart": bilgisayar_karti.sporcuAdi,
            "kullanici_puan": kp,
            "bilgisayar_puan": bp,
            "sonuc": sonuc
        })

        self.mevcutTur += 1

        if self.mevcutTur > self.toplamTur:
            mesaj += "\n\nOYUN BİTTİ!\n" + self.kazanan_belirle()

        return {"bitti": self.mevcutTur > self.toplamTur, "mesaj": mesaj}

    def kazanan_belirle(self):
        k = self.kullanici
        b = self.bilgisayar

        if k.skor > b.skor:
            return f"Kazanan Kullanıcı! Skor: {k.skor} - {b.skor}"
        elif b.skor > k.skor:
            return f"Kazanan Bilgisayar! Skor: {b.skor} - {k.skor}"

        if k.toplamGalibiyet > b.toplamGalibiyet:
            return "Kazanan Kullanıcı (toplam galibiyet)"
        elif b.toplamGalibiyet > k.toplamGalibiyet:
            return "Kazanan Bilgisayar (toplam galibiyet)"

        if k.galibiyetSerisiSayisi > b.galibiyetSerisiSayisi:
            return "Kazanan Kullanıcı (seri sayısı)"
        elif b.galibiyetSerisiSayisi > k.galibiyetSerisiSayisi:
            return "Kazanan Bilgisayar (seri sayısı)"

        k_enerji = sum(x.enerji for x in k.kartListesi)
        b_enerji = sum(x.enerji for x in b.kartListesi)
        if k_enerji > b_enerji:
            return "Kazanan Kullanıcı (kalan enerji)"
        elif b_enerji > k_enerji:
            return "Kazanan Bilgisayar (kalan enerji)"

        k_lvl3 = sum(1 for x in k.kartListesi if x.seviye == 3)
        b_lvl3 = sum(1 for x in b.kartListesi if x.seviye == 3)
        if k_lvl3 > b_lvl3:
            return "Kazanan Kullanıcı (seviye 3 kart sayısı)"
        elif b_lvl3 > k_lvl3:
            return "Kazanan Bilgisayar (seviye 3 kart sayısı)"

        if k.ozelYetenekliGalibiyet > b.ozelYetenekliGalibiyet:
            return "Kazanan Kullanıcı (özel yetenekli galibiyet)"
        elif b.ozelYetenekliGalibiyet > k.ozelYetenekliGalibiyet:
            return "Kazanan Bilgisayar (özel yetenekli galibiyet)"

        if k.toplamBeraberlik < b.toplamBeraberlik:
            return "Kazanan Kullanıcı (daha az beraberlik)"
        elif b.toplamBeraberlik < k.toplamBeraberlik:
            return "Kazanan Bilgisayar (daha az beraberlik)"

        return "Oyun berabere bitti."


# =========================================================
# PYQT ARAYÜZ
# =========================================================

class AnaPencere(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Akıllı Sporcu Kart Ligi Simülasyonu")
        self.setGeometry(100, 80, 1450, 850)

        self.oyun = None

        self.lblBaslik = QLabel("AKILLI SPORCU KART LİGİ")
        self.lblBaslik.setAlignment(Qt.AlignCenter)
        self.lblBaslik.setStyleSheet("font-size: 22px; font-weight: bold; color: #1f3b73;")

        self.lblDurum = QLabel("Dosya yükle ve oyunu başlat.")
        self.lblSkor = QLabel("Toplam Skor -> Kullanıcı: 0 | Bilgisayar: 0")
        self.lblTur = QLabel("Tur: -")
        self.lblMoral = QLabel("Moral -> Kullanıcı: 60 | Bilgisayar: 60")

        self.cmbZorluk = QComboBox()
        self.cmbZorluk.addItems(["Kolay", "Orta"])

        self.cmbOzellik = QComboBox()

        self.btnDosya = QPushButton("CSV Yükle")
        self.btnBaslat = QPushButton("Oyunu Başlat")
        self.btnOyna = QPushButton("Seçili Kartı Oyna")
        self.btnBilgisayarKartlari = QPushButton("Bilgisayar Kartlarını Göster/Gizle")
        self.btnRapor = QPushButton("Rapor Göster")

        self.lstKullanici = QListWidget()
        self.lstBilgisayar = QListWidget()
        self.lstBilgisayar.setVisible(False)

        self.txtLog = QTextEdit()
        self.txtLog.setReadOnly(True)
        self.txtLog.setStyleSheet("font-size: 13px;")

        self.dosyaYolu = None

        self.arayuzu_kur()
        self.baglantilari_kur()

    def arayuzu_kur(self):
        ust = QHBoxLayout()
        ust.addWidget(QLabel("Zorluk:"))
        ust.addWidget(self.cmbZorluk)
        ust.addWidget(QLabel("Özellik Seçimi:"))
        ust.addWidget(self.cmbOzellik)
        ust.addWidget(self.btnDosya)
        ust.addWidget(self.btnBaslat)
        ust.addWidget(self.btnOyna)
        ust.addWidget(self.btnBilgisayarKartlari)
        ust.addWidget(self.btnRapor)

        bilgiler = QVBoxLayout()
        bilgiler.addWidget(self.lblDurum)
        bilgiler.addWidget(self.lblTur)
        bilgiler.addWidget(self.lblSkor)
        bilgiler.addWidget(self.lblMoral)

        kartlar = QGridLayout()
        kartlar.addWidget(QLabel("Kullanıcı Kartları"), 0, 0)
        kartlar.addWidget(QLabel("Bilgisayar Kartları"), 0, 1)
        kartlar.addWidget(self.lstKullanici, 1, 0)
        kartlar.addWidget(self.lstBilgisayar, 1, 1)

        ana = QVBoxLayout()
        ana.addWidget(self.lblBaslik)
        ana.addLayout(ust)
        ana.addLayout(bilgiler)
        ana.addLayout(kartlar)
        ana.addWidget(QLabel("Oyun Logu"))
        ana.addWidget(self.txtLog)

        self.setLayout(ana)

        self.lstKullanici.setSpacing(8)
        self.lstBilgisayar.setSpacing(8)

    def baglantilari_kur(self):
        self.btnDosya.clicked.connect(self.dosya_sec)
        self.btnBaslat.clicked.connect(self.oyunu_baslat)
        self.btnOyna.clicked.connect(self.secili_karti_oyna)
        self.btnBilgisayarKartlari.clicked.connect(self.bilgisayar_kartlarini_toggle)
        self.btnRapor.clicked.connect(self.rapor_goster)

    def dosya_sec(self):
        dosya, _ = QFileDialog.getOpenFileName(self, "CSV Seç", "", "CSV Files (*.csv)")
        if dosya:
            self.dosyaYolu = dosya
            self.lblDurum.setText(f"Seçilen dosya: {dosya}")

    def oyunu_baslat(self):
        if not self.dosyaYolu:
            QMessageBox.warning(self, "Uyarı", "Önce CSV dosyası seç.")
            return

        try:
            kartlar = VeriOkuyucu.dosyadan_oku(self.dosyaYolu)
        except Exception as e:
            QMessageBox.critical(self, "Dosya Hatası", str(e))
            return

        if len(kartlar) != 24:
            QMessageBox.warning(self, "Uyarı", "Dosyada toplam 24 kart olmalı.")
            return

        zorluk = self.cmbZorluk.currentText()
        strateji = KolayStrateji() if zorluk == "Kolay" else OrtaStrateji()

        self.oyun = OyunYonetici(kartlar, strateji)
        self.txtLog.clear()
        self.txtLog.append("Oyun başlatıldı.")
        self.ekrani_guncelle()

    def ekrani_guncelle(self):
        if not self.oyun:
            return

        self.lstKullanici.clear()
        self.lstBilgisayar.clear()
        self.cmbOzellik.clear()

        branş = self.oyun.mevcut_branş()
        self.lblTur.setText(f"Tur: {self.oyun.mevcutTur} | Branş: {branş}")
        self.lblSkor.setText(
            f"Toplam Skor -> Kullanıcı: {self.oyun.kullanici.skor} | Bilgisayar: {self.oyun.bilgisayar.skor}"
        )
        self.lblMoral.setText(
            f"Moral -> Kullanıcı: {self.oyun.kullanici.moral} | Bilgisayar: {self.oyun.bilgisayar.moral}"
        )

        kullanici_uygun = self.oyun.kullanici.uygun_kartlar(branş) if branş else []
        if kullanici_uygun:
            ozellikler = list(kullanici_uygun[0].ozellikler().keys())
            self.cmbOzellik.addItems(ozellikler)

        for kart in self.oyun.kullanici.kartListesi:
            sonuc = None
            if self.oyun.son_kullanici_karti_id == kart.sporcuID:
                if self.oyun.son_kazanan == "kullanici":
                    sonuc = "kazandi"
                elif self.oyun.son_kazanan == "bilgisayar":
                    sonuc = "kaybetti"
                else:
                    sonuc = "berabere"

            widget = KartWidget(kart, sonuc)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.lstKullanici.addItem(item)
            self.lstKullanici.setItemWidget(item, widget)

        for kart in self.oyun.bilgisayar.kartListesi:
            sonuc = None
            if self.oyun.son_bilgisayar_karti_id == kart.sporcuID:
                if self.oyun.son_kazanan == "bilgisayar":
                    sonuc = "kazandi"
                elif self.oyun.son_kazanan == "kullanici":
                    sonuc = "kaybetti"
                else:
                    sonuc = "berabere"

            widget = KartWidget(kart, sonuc)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.lstBilgisayar.addItem(item)
            self.lstBilgisayar.setItemWidget(item, widget)

    def secili_karti_oyna(self):
        if not self.oyun:
            QMessageBox.warning(self, "Uyarı", "Önce oyunu başlat.")
            return

        index = self.lstKullanici.currentRow()
        if index < 0:
            QMessageBox.warning(self, "Uyarı", "Bir kart seç.")
            return

        kart = self.oyun.kullanici.kartListesi[index]
        secili_ozellik = self.cmbOzellik.currentText()

        eski_k_skor = self.oyun.kullanici.skor
        eski_b_skor = self.oyun.bilgisayar.skor

        sonuc = self.oyun.tur_oyna(kart, secili_ozellik)

        yeni_k_skor = self.oyun.kullanici.skor
        yeni_b_skor = self.oyun.bilgisayar.skor

        k_artis = yeni_k_skor - eski_k_skor
        b_artis = yeni_b_skor - eski_b_skor

        self.txtLog.append(sonuc["mesaj"])
        self.txtLog.append(f"Bu tur puan değişimi -> Kullanıcı: +{k_artis} | Bilgisayar: +{b_artis}")
        self.txtLog.append(f"Güncel toplam skor -> Kullanıcı: {yeni_k_skor} | Bilgisayar: {yeni_b_skor}")
        self.txtLog.append("-" * 80)

        self.ekrani_guncelle()

        if sonuc["bitti"]:
            QMessageBox.information(self, "Oyun Sonu", sonuc["mesaj"])

    def bilgisayar_kartlarini_toggle(self):
        self.lstBilgisayar.setVisible(not self.lstBilgisayar.isVisible())

    def rapor_goster(self):
        if not self.oyun:
            QMessageBox.warning(self, "Uyarı", "Henüz oyun yok.")
            return

        rapor = self.oyun.istatistik.rapor_olustur()
        msg = QMessageBox(self)
        msg.setWindowTitle("Maç Raporu")
        msg.setText(rapor[:3000] if len(rapor) > 3000 else rapor)
        msg.exec_()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec_())
