/* Foreground, user-initiated alerts only; no background notification claim. */
export async function enableSound(): Promise<AudioContext> {
  const audio=new AudioContext();await audio.resume();return audio;
}
export function announce(audio: AudioContext | null){
  if(!audio||audio.state!=='running')return;
  const oscillator=audio.createOscillator();const volume=audio.createGain();oscillator.connect(volume);volume.connect(audio.destination);
  oscillator.frequency.value=660;volume.gain.setValueAtTime(.08,audio.currentTime);volume.gain.exponentialRampToValueAtTime(.001,audio.currentTime+.35);
  oscillator.start();oscillator.stop(audio.currentTime+.35);
}
