/**
 * n8n Dynamic Caption Normalizer & Brand Router
 * Input: $input.item.json containing { brand_id, slug, caption, subgenre, bpm, video_path }
 */

const item = $input.item.json;
const brandId = item.brand_id || "phonk_pipeline";
const rawCaption = item.caption || "Check out this new release!";
const title = (item.slug || "New Track").replace(/_/g, ' ').toUpperCase();
const bpm = item.bpm || 155;

// Load config or use fallbacks if not directly injected
const brandsConfig = {
  phonk_pipeline: {
    core: "#phonk #phonkmusic #gymphonk #driftphonk #phonkbeat",
    instagram: "#gymmotivation #phonkedit #carphonk #bodybuilding #darkphonk #bassboosted",
    youtube: "#shorts #shortvideo #phonkmusic #driftphonk #phonk2026",
    tiktok: "#fyp #viral #phonk #gymtok #cartok #phonktok #phonkdrip"
  },
  publixion: {
    core: "#publixion #publishing #contentcreator #digitalmedia #growth",
    instagram: "#media #digitalstrategy #contentmarketing #creators",
    youtube: "#shorts #media #contentcreation #business",
    linkedin: "#DigitalPublishing #MediaGrowth #ContentStrategy #Publixion"
  },
  myfitnessleap: {
    core: "#fitness #health #workout #gym #fitnessmotivation",
    instagram: "#fitfam #gymlife #training #bodybuilding #healthylifestyle",
    youtube: "#shorts #fitness #gym #workoutmotivation #health",
    tiktok: "#gymtok #fitnesstok #workout #health #fyp",
    linkedin: "#CorporateWellness #HealthAndFitness #PeakPerformance #Leadership"
  },
  neurostackos: {
    core: "#nootropics #biohacking #neuroscience #focus #productivity",
    youtube: "#shorts #biohacking #productivity #brainperformance #neuroscience",
    tiktok: "#biohack #focus #adhd #mentalclarity #brainpower #fyp",
    linkedin: "#Biohacking #Neuroscience #CognitivePerformance #HighPerformance #Focus"
  }
};

const tags = brandsConfig[brandId] || brandsConfig.phonk_pipeline;

// 1. YouTube Shorts Payload (#shorts strictly in first 80 chars)
const youtubeCaption = `${title} | ${tags.youtube}\n\n${rawCaption}\n\n${tags.core}`;

// 2. Instagram Reels Payload (Clean Hook + Spaced Hashtags)
const instagramCaption = `🔥 ${title}\n${rawCaption}\n.\n.\n.\n.\n.\n${tags.core} ${tags.instagram || ''}`;

// 3. TikTok Reels Payload (Emoji hook + high-velocity #fyp cluster)
const tiktokCaption = `⚡ ${title} ⚡\n${rawCaption}\n\n${tags.core} ${tags.tiktok || ''}`;

// 4. Facebook Reels Payload (Conversational, max 3 tags)
const facebookCaption = `${title} - ${rawCaption}\n\n${tags.core}`;

// 5. LinkedIn Video Payload (Professional formatting + industry hashtags)
const linkedinCaption = `${title}\n\n${rawCaption}\n\n${tags.linkedin || tags.core}`;

return {
  json: {
    ...item,
    normalized_captions: {
      youtube: youtubeCaption,
      instagram: instagramCaption,
      tiktok: tiktokCaption,
      facebook: facebookCaption,
      linkedin: linkedinCaption
    },
    video_path: item.video_path || `/data/videos/${item.slug}.mp4`
  }
};
