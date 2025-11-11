/**
 * BassEngine v1.0 - Pure Bass Detection
 * מנוע עצמאי לזיהוי תווי בס בלבד
 */

class BassEngine {
  constructor() {
    this.NOTES_SHARP = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
    this._hannCache = {};
  }

  async detectBass(audioBuffer, options = {}) {
    const opts = {
      channelData: options.channelData || null,
      sampleRate: options.sampleRate || null,
      minStability: options.minStability || 3,
      minConfidence: options.minConfidence || 0.5
    };

    const audioData = this.processAudio(audioBuffer, opts.channelData, opts.sampleRate);
    const feats = this.extractFeatures(audioData);
    const bassTimeline = this.createBassTimeline(feats, opts);

    return {
      bassNotes: bassTimeline,
      duration: audioData.duration,
      bpm: audioData.bpm,
      stats: {
        totalBassChanges: bassTimeline.length,
        averageDuration: bassTimeline.length > 0 ? audioData.duration / bassTimeline.length : 0
      }
    };
  }

  processAudio(audioBuffer, channelData, sampleRate) {
    let mono;
    if (channelData && sampleRate) {
      mono = channelData;
      const sr0 = sampleRate;
      const sr = 22050;
      const x = this.resampleLinear(mono, sr0, sr);
      const bpm = this.estimateTempo(x, sr);
      return { x, sr, bpm, duration: x.length / sr };
    }

    const channels = audioBuffer.numberOfChannels || 1;
    mono = (channels === 1) ? audioBuffer.getChannelData(0) : this.mixStereo(audioBuffer);
    const sr0 = audioBuffer.sampleRate || 44100;
    const sr = 22050;
    const x = this.resampleLinear(mono, sr0, sr);
    const bpm = this.estimateTempo(x, sr);
    return { x, sr, bpm, duration: x.length / sr };
  }

  estimateTempo(x, sr) {
    const hop = Math.floor(0.1 * sr);
    const frames = [];
    for (let s = 0; s + 4096 <= x.length; s += hop) {
      let e = 0;
      for (let i = 0; i < 4096; i++) e += x[s + i] * x[s + i];
      frames.push(e);
    }
    if (frames.length < 4) return 120;

    const minLag = Math.floor(0.3 / (hop / sr));
    const maxLag = Math.floor(2.0 / (hop / sr));
    let bestLag = minLag;
    let bestR = -Infinity;

    for (let lag = minLag; lag <= maxLag; lag++) {
      let r = 0;
      for (let i = 0; i < frames.length - lag; i++) {
        r += frames[i] * frames[i + lag];
      }
      if (r > bestR) {
        bestR = r;
        bestLag = lag;
      }
    }

    const bpm = 60 / (bestLag * (hop / sr));
    if (!isFinite(bpm)) return 120;
    return Math.max(60, Math.min(200, Math.round(bpm)));
  }

  extractFeatures(audioData) {
    const { x, sr } = audioData;
    const hop = Math.floor(0.10 * sr);
    const win = 4096;

    if (!this._hannCache[win]) {
      const hann = new Float32Array(win);
      for (let i = 0; i < win; i++) {
        hann[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (win - 1)));
      }
      this._hannCache[win] = hann;
    }
    const hann = this._hannCache[win];

    const frames = [];
    for (let s = 0; s + win <= x.length; s += hop) {
      frames.push(x.subarray(s, s + win));
    }

    const bassPc = [];
    const frameE = [];

    for (let i = 0; i < frames.length; i++) {
      const frame = frames[i];
      const windowed = new Float32Array(win);
      for (let k = 0; k < win; k++) {
        windowed[k] = frame[k] * hann[k];
      }

      let en = 0;
      for (let k = 0; k < win; k++) en += windowed[k] * windowed[k];
      frameE.push(en);

      const { mags, N } = this.fft(windowed);
      bassPc.push(this.estimateBassF0(mags, sr, N));
    }

    const thrE = this.percentile(frameE, 40);
    for (let i = 1; i < bassPc.length - 1; i++) {
      const v = bassPc[i];
      if (v < 0 || frameE[i] < thrE || (bassPc[i - 1] !== v && bassPc[i + 1] !== v)) {
        bassPc[i] = -1;
      }
    }

    const percentiles = {
      p30: this.percentile(frameE, 30),
      p40: this.percentile(frameE, 40),
      p50: this.percentile(frameE, 50),
      p70: this.percentile(frameE, 70)
    };

    return { bassPc, frameE, hop, sr, percentiles };
  }

  estimateBassF0(mags, sr, N) {
    const fmin = 40;
    const fmax = 250;
    const win = N;
    const yLP = new Float32Array(win);

    for (let b = 1; b < mags.length; b++) {
      const f = b * sr / N;
      if (f <= fmax) {
        const omega = 2 * Math.PI * f / sr;
        for (let n = 0; n < win; n++) {
          yLP[n] += mags[b] * Math.cos(omega * n);
        }
      }
    }

    const f0minLag = Math.floor(sr / fmax);
    const f0maxLag = Math.floor(sr / fmin);
    let bestLag = -1;
    let bestR = -1;

    let mean = 0;
    for (let n = 0; n < win; n++) mean += yLP[n];
    mean /= win || 1;

    let denom = 0;
    for (let n = 0; n < win; n++) {
      const d = yLP[n] - mean;
      denom += d * d;
    }
    denom = denom || 1e-9;

    for (let lag = f0minLag; lag <= f0maxLag; lag++) {
      let r = 0;
      for (let n = 0; n < win - lag; n++) {
        const a = yLP[n] - mean;
        const b = yLP[n + lag] - mean;
        r += a * b;
      }
      r /= denom;
      if (r > bestR) {
        bestR = r;
        bestLag = lag;
      }
    }

    if (bestLag > 0) {
      const f0 = sr / bestLag;
      if (f0 >= fmin && f0 <= fmax) {
        const midiF0 = 69 + 12 * Math.log2(f0 / 440);
        return ((Math.round(midiF0) % 12) + 12) % 12;
      }
    }

    return -1;
  }

  fft(input) {
    let n = input.length;
    let N = 1;
    while (N < n) N <<= 1;

    const re = new Float32Array(N);
    const im = new Float32Array(N);
    re.set(input);

    let j = 0;
    for (let i = 0; i < N; i++) {
      if (i < j) {
        [re[i], re[j]] = [re[j], re[i]];
        [im[i], im[j]] = [im[j], im[i]];
      }
      let m = N >> 1;
      while (m >= 1 && j >= m) {
        j -= m;
        m >>= 1;
      }
      j += m;
    }

    for (let len = 2; len <= N; len <<= 1) {
      const ang = -2 * Math.PI / len;
      const wlr = Math.cos(ang);
      const wli = Math.sin(ang);
      for (let i = 0; i < N; i += len) {
        let wr = 1;
        let wi = 0;
        for (let k = 0; k < (len >> 1); k++) {
          const uRe = re[i + k];
          const uIm = im[i + k];
          const vRe = re[i + k + (len >> 1)] * wr - im[i + k + (len >> 1)] * wi;
          const vIm = re[i + k + (len >> 1)] * wi + im[i + k + (len >> 1)] * wr;

          re[i + k] = uRe + vRe;
          im[i + k] = uIm + vIm;
          re[i + k + (len >> 1)] = uRe - vRe;
          im[i + k + (len >> 1)] = uIm - vIm;

          const nwr = wr * wlr - wi * wli;
          wi = wr * wli + wi * wlr;
          wr = nwr;
        }
      }
    }

    const mags = new Float32Array(N >> 1);
    for (let k = 0; k < mags.length; k++) {
      mags[k] = Math.hypot(re[k], im[k]);
    }

    return { mags, N };
  }

  createBassTimeline(feats, options = {}) {
    const { bassPc, frameE, hop, sr, percentiles } = feats;
    const minStability = options.minStability || 3;
    const minConfidence = options.minConfidence || 0.5;
    
    const energyThreshold = percentiles.p40 || this.percentile(frameE, 40);
    
    const timeline = [];
    let currentBass = -1;
    let currentStart = 0;
    let stabilityCount = 0;
    
    for (let i = 0; i < bassPc.length; i++) {
      const bass = bassPc[i];
      const energy = frameE[i];
      
      if (bass < 0 || energy < energyThreshold) {
        if (currentBass >= 0 && stabilityCount >= minStability) {
          const startTime = currentStart * (hop / sr);
          const endTime = i * (hop / sr);
          const duration = endTime - startTime;
          
          timeline.push({
            note: this.NOTES_SHARP[currentBass],
            notePc: currentBass,
            startTime,
            endTime,
            duration,
            confidence: Math.min(1.0, stabilityCount / 10),
            startFrame: currentStart,
            endFrame: i
          });
        }
        
        currentBass = -1;
        stabilityCount = 0;
        continue;
      }
      
      if (bass !== currentBass) {
        if (currentBass >= 0 && stabilityCount >= minStability) {
          const startTime = currentStart * (hop / sr);
          const endTime = i * (hop / sr);
          const duration = endTime - startTime;
          
          timeline.push({
            note: this.NOTES_SHARP[currentBass],
            notePc: currentBass,
            startTime,
            endTime,
            duration,
            confidence: Math.min(1.0, stabilityCount / 10),
            startFrame: currentStart,
            endFrame: i
          });
        }
        
        currentBass = bass;
        currentStart = i;
        stabilityCount = 1;
      } else {
        stabilityCount++;
      }
    }
    
    if (currentBass >= 0 && stabilityCount >= minStability) {
      const startTime = currentStart * (hop / sr);
      const endTime = bassPc.length * (hop / sr);
      const duration = endTime - startTime;
      
      timeline.push({
        note: this.NOTES_SHARP[currentBass],
        notePc: currentBass,
        startTime,
        endTime,
        duration,
        confidence: Math.min(1.0, stabilityCount / 10),
        startFrame: currentStart,
        endFrame: bassPc.length
      });
    }
    
    return timeline.filter(note => note.confidence >= minConfidence);
  }

  mixStereo(audioBuffer) {
    const left = audioBuffer.getChannelData(0);
    const right = audioBuffer.getChannelData(1);
    const len = Math.min(left.length, right.length);
    const mono = new Float32Array(len);
    for (let i = 0; i < len; i++) {
      mono[i] = 0.5 * (left[i] + right[i]);
    }
    return mono;
  }

  resampleLinear(samples, fromRate, toRate) {
    if (!samples || fromRate === toRate) return samples;
    const ratio = fromRate / toRate;
    const newLength = Math.max(1, Math.floor(samples.length / ratio));
    const resampled = new Float32Array(newLength);

    for (let i = 0; i < newLength; i++) {
      const srcIndex = i * ratio;
      const i0 = Math.floor(srcIndex);
      const i1 = Math.min(i0 + 1, samples.length - 1);
      const t = srcIndex - i0;
      resampled[i] = samples[i0] * (1 - t) + samples[i1] * t;
    }

    return resampled;
  }

  percentile(arr, p) {
    const a = (arr || []).filter(v => Number.isFinite(v)).sort((x, y) => x - y);
    if (!a.length) return 0;
    const idx = Math.floor((p / 100) * (a.length - 1));
    return a[idx];
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = BassEngine;
}