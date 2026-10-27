import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('Chatbot/.env')

client = OpenAI(
    base_url='https://openrouter.ai/api/v1',
    api_key=os.getenv('OPENROUTER_API_KEY')
)

sample_ocr = """
'Alif lanrn raa, (inilah) suatu kitab yilW ayat-ctyclhyd disltiln dengan rapi suta ilijelasl<m seccffo terperinci, lmg diarnurl<m dari sisi (/.Jllah) Y*gMahaBijakana lagiMaha talnt." (Qs. Huud [11]: 1)
Talrwil firman Allah: t fi ,y,rii.? ,*:;6A eg j, ,$ ",lttf toam raa, (inilah) suatu kitab yang ayat-ayatnya disusun dengan rapi serta dijelaskan secara terperinci, yang diturunkan dari sisi (Allah) Yang Maha Bijahsana lagi Maha tahu."
Abu Ja'far berkata: Kami telah menyebutkan tentang perbedaan pendapat yang terjadi di antara ahli tafsir dalam menakwilkan ayat: jl *,lty laam raa", dan pendapat yang benar menurut kami dalam menakwilkan ayat yang demikian itu harus berdasarkan riwayat-riwayat yang shahih. Dengan demikian, tidak perlu diulas kembali dalam pembahasan ini.
Firman Allah: ,^S:;E$ lE "(Inilah) suatu Kitab yang ayat-ayatnya disusun dengan rapi," maksudnya adalah sebuah kitab yang diturunkan kepada nabi-Nya, yaitu Nabi Muhammad SAW, dan kitab itu adalah Al Qur'an. Di-rafa'kannya lafazh Kitab maksudnya adalah .7tf tj.o "Ini kitab."
Adapun firman Allah: ti$ ? '^':; S.A "Yang ayat-ayat-Nya disusun dengan rapi serta dijelaskan secara terperinci." Para ahli tafsir berbeda pendapat dalam menakwilkan ayat ini.
"""

prompt = f"""Kamu adalah asisten ahli restorasi teks kitab Tafsir Ath-Thabari bahasa Indonesia.
Teks berikut berasal dari OCR buku cetak terjemahan Tafsir Ath-Thabari (Pustaka Azzam).
Ayat yang sedang dibahas adalah Surah Hud ayat 1:
الٓر ۚ كِتَـٰبٌ أُحْكِمَتْ ءَايَـٰتُهُۥ ثُمَّ فُصِّلَتْ مِن لَّدُنْ حَكِيمٍ خَبِيرٍ

TUGAS:
1. Kembalikan semua frasa/kalimat Arab yang rusak oleh OCR menjadi teks Arab asli yang benar dan jelas (misal teks Arab ayat, potongan firman Allah, lafazh muqaththa'ah).
2. Perbaiki terjemahan ayat dan typo OCR bahasa Indonesia agar enak dibaca dan baku.
3. Pertahankan struktur asli, nomor riwayat, perawi, dan jangan meringkas isi sama sekali.

Teks input:
{sample_ocr}
"""

resp = client.chat.completions.create(
    model='openai/gpt-4o-mini',
    messages=[{'role': 'user', 'content': prompt}],
    temperature=0.2
)

print('=== RESTORED RESULT ===')
print(resp.choices[0].message.content)
