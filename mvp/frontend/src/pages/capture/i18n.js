// Bilingual strings for the Capture flow.
// EN/KH copy sourced verbatim from docs/prototypes/Roeung Capture.html.
// Keys with an empty `kh` value are not yet translated (see seed.py for the
// same convention) and fall back to English via `t()`.

export const strings = {
  en: {
    appSub: 'Sea family stories',
    homeHeading: 'Add your voice to the family book.',
    recordTitle: 'Record a story', recordKh: 'ថតរឿង', recordSub: 'Use your microphone',
    uploadTitle: 'Upload audio', uploadKh: 'ផ្ទុកឡើង', uploadSub: 'mp3, m4a, wav',
    recentlyAdded: 'Recently added',
    consentTitle: 'Consent',
    consentLead: 'Before we begin',
    consentBodyRecordTemplate: '“We’re about to record {{name}}’s story. They have agreed to be recorded, and for this story to be shared with the family.”',
    consentBodyUpload: '“The person in this recording agreed to have it shared with the Sea family.”',
    consentMeta: 'The narrator’s name and your confirmation are logged with a timestamp. You can cancel now — nothing has started yet.',
    narratorLabel: 'Who is this story about?',
    narratorPlaceholder: 'Narrator’s name',
    yesAgreed: 'Yes, they’ve agreed', cancel: 'Cancel',
    recording: 'Recording', maxMin: 'max 60 min', tapStop: 'Tap to stop', clickStop: 'Click to stop',
    discard: 'Discard recording', discardCancel: 'Discard & cancel',
    noise: 'Background noise detected',
    noiseDesk: 'Background noise detected — try moving to a quieter room',
    micError: 'Couldn’t access your microphone. Check your browser permissions and try again.',
    uploadHead: 'Upload audio', chooseFile: 'Choose an audio file', fileLimit: 'mp3, m4a, wav · max 500MB',
    dropHere: 'Drop your audio file here', orBrowse: 'or click to browse',
    uploading: 'Uploading…', change: 'Change', continueBtn: 'Continue',
    fileTypeError: 'Please choose an mp3, m4a, or wav file.',
    fileSizeError: 'That file is larger than 500MB.',
    tagTitle: 'Quick tag', whoAbout: 'Who is this story about?',
    preselected: 'Pre-selected by recorder', members: 'Sea family members', someoneElse: '+ Someone else',
    addPerson: 'Add', someoneElsePlaceholder: 'Their name',
    tagTip: 'Keepers can add or edit tags during review.', next: 'Next', skip: 'Skip for now',
    confirmTitle: 'Confirm & send', confirmSub: 'Have a listen before you send.',
    duration: 'Duration', capturedBy: 'Captured by', liveRec: 'Live recording', fileUp: 'File upload',
    peopleTagged: 'People tagged', consentLogged: 'Consent logged',
    sendKeepers: 'Send to Keepers', deleteRec: 'Delete recording',
    delTitle: 'Delete this recording?', delBody: 'This can’t be undone. The audio will be permanently deleted — nothing is sent to the Keepers.',
    yesDelete: 'Yes, delete it', keepIt: 'Keep it',
    sendError: 'Something went wrong sending your story. Please try again.',
    sentTitle: 'Your story is with the Keepers', sentBody: 'The Sea family Keepers have been notified and will review it soon.',
    reviewTime: 'Estimated review time: 1–3 days', recordAnother: 'Record another story', backHome: 'Back to home',
    audioLangLabel: 'What language is the story in?',
    audioLangKh: 'ខ្មែរ Khmer', audioLangEn: 'English',
    minWord: 'min', secWord: 'sec', noTags: '—',
  },
  kh: {
    appSub: 'រឿងគ្រួសារ Sea',
    homeHeading: 'បន្ថែមសំឡេងរបស់អ្នកទៅក្នុងសៀវភៅគ្រួសារ។',
    recordTitle: 'ថតរឿង', recordKh: 'Record a story', recordSub: 'ប្រើមីក្រូហ្វូនរបស់អ្នក',
    uploadTitle: 'ផ្ទុកសំឡេង', uploadKh: 'Upload audio', uploadSub: 'mp3, m4a, wav',
    recentlyAdded: 'បន្ថែមថ្មីៗ',
    consentTitle: 'ការយល់ព្រម',
    consentLead: 'មុនពេលយើងចាប់ផ្ដើម',
    consentBodyRecordTemplate: '«យើងរៀបនឹងថតរឿងរបស់ {{name}}។ គាត់បានយល់ព្រមឲ្យថត និងឲ្យចែករំលែករឿងនេះជាមួយគ្រួសារ។»',
    consentBodyUpload: '«អ្នកនៅក្នុងការថតនេះបានយល់ព្រមឲ្យចែករំលែកវាជាមួយគ្រួសារ Sea។»',
    consentMeta: 'ឈ្មោះអ្នកនិទាន និងការបញ្ជាក់របស់អ្នកនឹងត្រូវកត់ត្រាជាមួយម៉ោងកំណត់។ អ្នកអាចបោះបង់ឥឡូវនេះ — មិនទាន់មានអ្វីចាប់ផ្ដើមទេ។',
    narratorLabel: 'រឿងនេះនិយាយអំពីអ្នកណា?',
    narratorPlaceholder: '',
    yesAgreed: 'បាទ/ចាស ពួកគេបានយល់ព្រម', cancel: 'បោះបង់',
    recording: 'កំពុងថត', maxMin: 'អតិបរមា ៦០ នាទី', tapStop: 'ប៉ះដើម្បីបញ្ឈប់', clickStop: 'ចុចដើម្បីបញ្ឈប់',
    discard: 'បោះបង់ការថត', discardCancel: 'បោះបង់ & ចេញ',
    noise: 'រកឃើញសំឡេងរំខាន',
    noiseDesk: 'រកឃើញសំឡេងរំខាន — សាកល្បងផ្លាស់ទៅបន្ទប់ស្ងាត់ជាង',
    micError: '',
    uploadHead: 'ផ្ទុកសំឡេង', chooseFile: 'ជ្រើសរើសឯកសារសំឡេង', fileLimit: 'mp3, m4a, wav · អតិបរមា 500MB',
    dropHere: 'ទម្លាក់ឯកសារសំឡេងនៅទីនេះ', orBrowse: 'ឬចុចដើម្បីរកមើល',
    uploading: 'កំពុងផ្ទុក…', change: 'ប្ដូរ', continueBtn: 'បន្ត',
    fileTypeError: '',
    fileSizeError: '',
    tagTitle: 'ដាក់ស្លាក', whoAbout: 'រឿងនេះនិយាយអំពីអ្នកណា?',
    preselected: 'ជ្រើសរើសដោយអ្នកថត', members: 'សមាជិកគ្រួសារ Sea', someoneElse: '+ នរណាម្នាក់ផ្សេង',
    addPerson: '', someoneElsePlaceholder: '',
    tagTip: 'អ្នកថែរក្សាអាចបន្ថែម ឬកែស្លាកនៅពេលត្រួតពិនិត្យ។', next: 'បន្ទាប់', skip: 'រំលងសិន',
    confirmTitle: 'បញ្ជាក់ & ផ្ញើ', confirmSub: 'ស្ដាប់ឡើងវិញមុនពេលផ្ញើ។',
    duration: 'រយៈពេល', capturedBy: 'ថតដោយ', liveRec: 'ការថតផ្ទាល់', fileUp: 'ផ្ទុកឯកសារ',
    peopleTagged: 'មនុស្សដែលដាក់ស្លាក', consentLogged: 'ការយល់ព្រមកត់ត្រា',
    sendKeepers: 'ផ្ញើទៅអ្នកថែរក្សា', deleteRec: 'លុបការថត',
    delTitle: 'លុបការថតនេះ?', delBody: 'មិនអាចត្រឡប់វិញបានទេ។ សំឡេងនឹងត្រូវលុបជាអចិន្ត្រៃយ៍ — គ្មានអ្វីផ្ញើទៅអ្នកថែរក្សាទេ។',
    yesDelete: 'បាទ/ចាស លុបវា', keepIt: 'រក្សាទុក',
    sendError: '',
    sentTitle: 'រឿងរបស់អ្នកនៅជាមួយអ្នកថែរក្សាហើយ', sentBody: 'អ្នកថែរក្សាគ្រួសារ Sea ត្រូវបានជូនដំណឹង ហើយនឹងត្រួតពិនិត្យវាឆាប់ៗ។',
    reviewTime: 'ពេលត្រួតពិនិត្យ៖ ១–៣ ថ្ងៃ', recordAnother: 'ថតរឿងមួយទៀត', backHome: 'ត្រឡប់ទៅដើម',
    audioLangLabel: 'រឿងនេះនិយាយជាភាសាអ្វី?',
    audioLangKh: 'ខ្មែរ Khmer', audioLangEn: 'English',
    minWord: 'នាទី', secWord: 'វិនាទី', noTags: '—',
  },
};

export function t(lang, key, vars) {
  let str = strings[lang]?.[key];
  if (!str) str = strings.en[key] ?? key;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      str = str.replace(`{{${k}}}`, v);
    }
  }
  return str;
}
