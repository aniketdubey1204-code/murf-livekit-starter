/**
 * High-accuracy, self-contained Hindi (Devanagari) to Hinglish transliterator.
 * Zero external dependencies to prevent module build errors.
 */

// Common word dictionary for natural Hinglish spellings
const commonWordsMap: Record<string, string> = {
  'नमस्ते': 'namaste',
  'नमस्कार': 'namaskar',
  'धन्यवाद': 'dhanyavad',
  'शुक्रिया': 'shukriya',
  'हाँ': 'haan',
  'हां': 'haan',
  'नहीं': 'nahi',
  'नही': 'nahi',
  'क्या': 'kya',
  'कैसे': 'kaise',
  'कैसा': 'kaisa',
  'कैसी': 'kaisi',
  'कौन': 'kaun',
  'कहाँ': 'kahan',
  'कहां': 'kahan',
  'कब': 'kab',
  'क्यों': 'kyun',
  'दुकान': 'dukaan',
  'साथी': 'sathi',
  'सामान': 'saamaan',
  'ऑर्डर': 'order',
  'आर्डर': 'order',
  'चाहिए': 'chahiye',
  'मिलना': 'milna',
  'मिलेगा': 'milega',
  'किराना': 'kirana',
  'नमस्ते!': 'namaste!',
  'धन्यवाद!': 'dhanyavad!',
};

const charMap: Record<string, string> = {
  // Independent Vowels
  'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
  'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
  
  // Consonants
  'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
  'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
  'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
  'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
  'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
  'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
  'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
  
  // Nukta consonants
  'क़': 'q', 'ख़': 'kh', 'ग़': 'g', 'ज़': 'z', 'ड़': 'd', 'ढ़': 'dh', 'फ़': 'f',

  // Matras (Dependent Vowels)
  'ा': 'a', 'ि': 'i', 'ी': 'i', 'ु': 'u', 'ू': 'u', 'ृ': 'ri',
  'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
  
  // Modifiers
  'ं': 'n', 'ँ': 'n', 'ः': 'h',
  '्': '', // Halant
  '़': '', // Nukta
  
  // Numbers
  '०': '0', '१': '1', '२': '2', '३': '3', '४': '4', 
  '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
  
  // Punctuation
  '।': '.', '॥': '.'
};

function transliterateWord(word: string): string {
  // Clean word for dictionary lookup
  const cleanWord = word.replace(/[.,!?।]/g, '');
  const punctuation = word.slice(cleanWord.length);
  
  if (commonWordsMap[cleanWord]) {
    return commonWordsMap[cleanWord] + punctuation;
  }

  let res = '';
  const len = word.length;
  
  for (let i = 0; i < len; i++) {
    const char = word[i];
    const mapped = charMap[char];
    
    if (mapped !== undefined) {
      res += mapped;
      
      const code = char.charCodeAt(0);
      const isConsonant = (code >= 0x0915 && code <= 0x0939) || (code >= 0x0958 && code <= 0x095F);
      
      if (isConsonant) {
        const nextChar = word[i + 1];
        if (nextChar) {
          const nextCode = nextChar.charCodeAt(0);
          const isMatraOrHalant = (nextCode >= 0x093E && nextCode <= 0x094C) || nextCode === 0x094D;
          const isEndOrSpace = i === len - 1 || nextChar === ' ' || /[.,!?।]/.test(nextChar);
          
          // Add inherent 'a' sound if not followed by matra, halant, or end of word (schwa dropping rule)
          if (!isMatraOrHalant && !isEndOrSpace) {
            res += 'a';
          }
        }
      }
    } else {
      res += char;
    }
  }

  return res;
}

export function transliterateHindiToHinglish(text: string): string {
  if (!text) return text;

  // Split by space while preserving structure
  const words = text.split(' ');
  const transliterated = words.map(transliterateWord).join(' ');

  // Capitalize sentence start
  return transliterated.charAt(0).toUpperCase() + transliterated.slice(1);
}
