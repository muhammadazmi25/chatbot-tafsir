import { ALL_SURAHS } from './data/surahData';

const API_URL = '/api/v1';

// --- Tafsir Data API ---

export const getSurahList = async () => {
  try {
    const res = await fetch(`${API_URL}/tafsir/surahs`);
    if (res.ok) {
      const data = await res.json();
      // Map remote stats (unit count, etc.) onto ALL_SURAHS
      const mapStats = {};
      data.forEach(s => {
        mapStats[s.no_surah] = s;
      });
      return ALL_SURAHS.map(s => ({
        ...s,
        no_surah: s.nomor,
        nama_surah: s.namaLatin,
        nama_surah_arab: s.nama,
        arti_surah: s.arti,
        jumlah_unit: mapStats[s.nomor]?.jumlah_unit || 0,
        jumlah_ayat: s.jumlahAyat,
        revelation_place: s.tempatTurun,
      }));
    }
  } catch (err) {
    console.warn("Could not fetch remote surah stats, falling back to local dataset:", err);
  }

  // Fallback to local 114 surah dataset
  return ALL_SURAHS.map(s => ({
    ...s,
    no_surah: s.nomor,
    nama_surah: s.namaLatin,
    nama_surah_arab: s.nama,
    arti_surah: s.arti,
    jumlah_unit: s.hasTafsirThabari ? 10 : 0,
    jumlah_ayat: s.jumlahAyat,
    revelation_place: s.tempatTurun,
  }));
};

export const getAyatList = async (no_surah) => {
  let backendAyat = [];
  try {
    const res = await fetch(`${API_URL}/tafsir/surahs/${no_surah}/ayat`);
    if (res.ok) {
      backendAyat = await res.json();
    }
  } catch (err) {
    console.warn("Backend ayat fetch error:", err);
  }

  // Check if we already have complete terjemahan & teks_latin
  const hasTranslation = backendAyat.length > 0 && backendAyat[0].terjemahan;
  if (hasTranslation) {
    return backendAyat.map(b => ({
      ...b,
      audio: b.audio || `https://cdn.equran.id/audio-partial/Misyari-Rasyid-Al-Afasi/${String(no_surah).padStart(3, '0')}${String(b.no_ayat).padStart(3, '0')}.mp3`,
    }));
  }

  // If translation or transliteration is missing (e.g. older remote API), fetch from equran.id
  try {
    const eqRes = await fetch(`https://equran.id/api/v2/surat/${no_surah}`);
    if (eqRes.ok) {
      const eqData = await eqRes.json();
      const eqAyat = eqData?.data?.ayat || [];
      const eqMap = {};
      eqAyat.forEach(a => {
        eqMap[a.nomorAyat] = a;
      });

      if (backendAyat.length > 0) {
        // Merge backend's id_verse_tafsir & jumlah_unit with equran's clean Indonesian translation & audio
        return backendAyat.map(b => {
          const eq = eqMap[b.no_ayat] || {};
          return {
            ...b,
            teks_arab: b.teks_arab || eq.teksArab,
            teks_latin: b.teks_latin || eq.teksLatin,
            terjemahan: b.terjemahan || eq.teksIndonesia,
            audio: eq.audio?.['05'] || eq.audio?.['01'] || null, // Misyari Rasyid recitation
          };
        });
      } else {
        // Pure equran fallback if backend returned nothing (e.g. for surahs 1-10 before backend update)
        return eqAyat.map(a => ({
          id_verse: a.nomorAyat,
          no_ayat: a.nomorAyat,
          teks_arab: a.teksArab,
          teks_latin: a.teksLatin,
          terjemahan: a.teksIndonesia,
          id_verse_tafsir: null,
          jumlah_unit: 0,
          audio: a.audio?.['05'] || a.audio?.['01'] || null,
        }));
      }
    }
  } catch (e) {
    console.warn("equran API enrichment failed, returning raw backend ayat:", e);
  }

  return backendAyat.map(b => ({
    ...b,
    audio: b.audio || `https://cdn.equran.id/audio-partial/Misyari-Rasyid-Al-Afasi/${String(no_surah).padStart(3, '0')}${String(b.no_ayat).padStart(3, '0')}.mp3`,
  }));
};

export const getTafsirUnits = async (id_verse_tafsir) => {
  if (!id_verse_tafsir) return [];
  const res = await fetch(`${API_URL}/tafsir/verse/${id_verse_tafsir}/units`);
  if (!res.ok) throw new Error('Failed to fetch units');
  return res.json();
};

export const getUnitDetail = async (id_unit) => {
  const res = await fetch(`${API_URL}/tafsir/units/${id_unit}`);
  if (!res.ok) throw new Error('Failed to fetch unit detail');
  return res.json();
};

export const getFullVerseTafsir = async (id_verse_tafsir) => {
  if (!id_verse_tafsir) return null;
  const res = await fetch(`${API_URL}/tafsir/verse/${id_verse_tafsir}/full`);
  if (!res.ok) throw new Error('Failed to fetch full tafsir');
  return res.json();
};

// --- Sessions API ---

export const getSessions = async () => {
  const res = await fetch(`${API_URL}/sessions`);
  if (!res.ok) throw new Error('Failed to fetch sessions');
  return res.json();
};

export const getSessionMessages = async (session_uuid) => {
  const res = await fetch(`${API_URL}/sessions/${session_uuid}/messages`);
  if (!res.ok) throw new Error('Failed to fetch messages');
  return res.json();
};

export const deleteSession = async (session_uuid) => {
  const res = await fetch(`${API_URL}/sessions/${session_uuid}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete session');
  return res.json();
};
