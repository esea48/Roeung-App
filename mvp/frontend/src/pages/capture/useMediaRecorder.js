import { useCallback, useRef, useState } from 'react';
import { clearChunks, getChunks, saveChunk } from './audioChunkStore';

const TIMESLICE_MS = 2000;

function pickMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'];
  for (const type of candidates) {
    if (window.MediaRecorder?.isTypeSupported?.(type)) return type;
  }
  return '';
}

export function useMediaRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [error, setError] = useState(null);

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const sessionIdRef = useRef(null);
  const chunkIndexRef = useRef(0);
  const timerRef = useRef(null);
  const startedAtRef = useRef(0);
  const pausedElapsedRef = useRef(0);

  const tick = useCallback(() => {
    setElapsedSec(pausedElapsedRef.current + (Date.now() - startedAtRef.current) / 1000);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const sessionId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      sessionIdRef.current = sessionId;
      chunkIndexRef.current = 0;

      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          saveChunk(sessionId, chunkIndexRef.current, e.data);
          chunkIndexRef.current += 1;
        }
      };

      recorder.start(TIMESLICE_MS);
      startedAtRef.current = Date.now();
      pausedElapsedRef.current = 0;
      setElapsedSec(0);
      setIsRecording(true);
      setIsPaused(false);
      timerRef.current = setInterval(tick, 200);
    } catch (err) {
      setError(err);
    }
  }, [tick]);

  const pause = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== 'recording') return;
    recorder.pause();
    pausedElapsedRef.current = elapsedSec;
    clearInterval(timerRef.current);
    setIsPaused(true);
  }, [elapsedSec]);

  const resume = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== 'paused') return;
    recorder.resume();
    startedAtRef.current = Date.now();
    timerRef.current = setInterval(tick, 200);
    setIsPaused(false);
  }, [tick]);

  const cleanup = useCallback(() => {
    clearInterval(timerRef.current);
    timerRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
    setIsRecording(false);
    setIsPaused(false);
  }, []);

  const stop = useCallback(() => {
    const recorder = recorderRef.current;
    const sessionId = sessionIdRef.current;
    if (!recorder) return Promise.resolve(null);

    return new Promise((resolve) => {
      recorder.onstop = async () => {
        const durationSec = pausedElapsedRef.current + (Date.now() - startedAtRef.current) / 1000;
        cleanup();
        const chunks = await getChunks(sessionId);
        await clearChunks(sessionId);
        const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
        resolve({ blob, durationSec: isPaused ? pausedElapsedRef.current : durationSec });
      };
      recorder.stop();
    });
  }, [cleanup, isPaused]);

  const discard = useCallback(() => {
    const recorder = recorderRef.current;
    const sessionId = sessionIdRef.current;
    cleanup();
    if (sessionId) clearChunks(sessionId);
    if (recorder && recorder.state !== 'inactive') {
      try {
        recorder.stop();
      } catch {
        /* already stopped */
      }
    }
  }, [cleanup]);

  return { start, pause, resume, stop, discard, isRecording, isPaused, elapsedSec, error };
}
