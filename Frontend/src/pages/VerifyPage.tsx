import { useState, useRef, useCallback, useEffect } from 'react';
import {
  ScanLine, Camera, Upload, CheckCircle2, XCircle,
  AlertCircle, Image, X, CameraOff
} from 'lucide-react';
import { verifyPackage } from '../api';
import type { VerifyResponse } from '../api';
import { StatusBadge } from '../components/StatusBadge';

type Mode = 'choose' | 'camera' | 'upload';

function VerifyResult({ result, onReset }: { result: VerifyResponse; onReset: () => void }) {
  const both    = result.verified && result.registered;
  const neither = !result.verified && !result.registered;
  const cls     = both ? 'pass' : neither ? 'fail' : 'partial';
  const headline = both ? 'Fully Verified' : neither ? 'Verification Failed' : 'Partially Verified';

  return (
    <div>
      <div className={`verify-result ${cls}`}>
        <div className="flex items-center gap-3 mb-3">
          {both    && <CheckCircle2 size={28} style={{ color: 'var(--success)', flexShrink: 0 }} />}
          {neither && <XCircle      size={28} style={{ color: 'var(--danger)',  flexShrink: 0 }} />}
          {!both && !neither && <AlertCircle size={28} style={{ color: 'var(--warn)', flexShrink: 0 }} />}
          <div>
            <h2 style={{ color: both ? 'var(--success)' : neither ? 'var(--danger)' : 'var(--warn)', fontSize: '1.1rem' }}>
              {headline}
            </h2>
            <p className="text-sm" style={{ color: 'inherit', opacity: 0.7 }}>
              File: {result.filename}
            </p>
          </div>
        </div>

        <div className="verify-checks">
          <div className="verify-check-row">
            {result.verified
              ? <CheckCircle2 size={16} style={{ color: 'var(--success)' }} />
              : <XCircle size={16} style={{ color: 'var(--danger)' }} />}
            <span>
              <strong>Self-consistency:</strong>{' '}
              {result.verified
                ? `Code data found in OCR text (${result.matched_data})`
                : 'Code data not found in OCR text'}
            </span>
          </div>
          <div className="verify-check-row">
            {result.registered
              ? <CheckCircle2 size={16} style={{ color: 'var(--success)' }} />
              : <XCircle size={16} style={{ color: 'var(--danger)' }} />}
            <span>
              <strong>Registry check:</strong>{' '}
              {result.registered ? 'SKU found in database' : 'SKU not found in database'}
            </span>
          </div>
        </div>

        {result.matched_data && (
          <div style={{ marginTop: 14, padding: '10px 14px', background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)' }}>
            <div className="text-xs text-muted mb-1">Matched SKU</div>
            <span className="mono" style={{ fontSize: '1.1rem', color: 'var(--accent)' }}>{result.matched_data}</span>
          </div>
        )}

        <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <div className="text-xs text-muted mb-2 font-bold uppercase tracking-wider">Inference Performance ({(result.timing.total_ms / 1000).toFixed(2)}s)</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', fontSize: '0.8rem' }}>
             <div>
                <div className="text-muted">Total</div>
                <div className="mono text-accent">{result.timing.total_ms.toFixed(0)}ms</div>
             </div>
             <div>
                <div className="text-muted">Code Scan</div>
                <div className="mono">{result.timing.scan_ms.toFixed(0)}ms</div>
             </div>
             <div>
                <div className="text-muted">EasyOCR</div>
                <div className="mono">{result.timing.ocr_ms.toFixed(0)}ms</div>
             </div>
             <div>
                <div className="text-muted">DB Lookup</div>
                <div className="mono">{result.timing.db_ms.toFixed(0)}ms</div>
             </div>
          </div>
        </div>
      </div>

      {result.package && (
        <div className="card mt-4">
          <div className="card-header">
            <div className="card-title">Package Details</div>
            <StatusBadge status={result.package.status} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 24px' }}>
            {[
              ['SKU', result.package.sku],
              ['Sender', result.package.sender],
              ['Recipient', result.package.recipient],
              ['Contents', result.package.contents],
              ['Destination', result.package.destination],
              ['Routing Zone', result.package.routing_zone],
              ['Weight', `${result.package.weight_kg} kg`],
              ['Registered', new Date(result.package.created_at).toLocaleString()],
            ].map(([l, v]) => (
              <div key={l}>
                <div className="text-xs text-muted">{l}</div>
                <div className="text-sm" style={{ color: 'var(--text-primary)', marginTop: 2 }}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <div className="text-xs text-muted mb-2">
          Codes (1D/2D) detected: {result.details.barcodes_found.length} | OCR tokens: {result.details.texts_found.length}
        </div>
        <button id="verify-reset-btn" className="btn btn-secondary" onClick={onReset}>
          <ScanLine size={16} /> Scan Another
        </button>
      </div>
    </div>
  );
}

export default function VerifyPage() {
  const [mode, setMode]       = useState<Mode>('choose');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const [result, setResult]   = useState<VerifyResponse | null>(null);

  // Camera state
  const videoRef              = useRef<HTMLVideoElement>(null);
  const streamRef             = useRef<MediaStream | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState('');

  // Upload state
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview]   = useState<string | null>(null);
  const [file, setFile]         = useState<File | null>(null);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    setCameraReady(false);
  }, []);

  const startCamera = useCallback(async () => {
    setCameraError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'environment',
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        } 
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setCameraReady(true);
      }
    } catch {
      setCameraError('Could not access camera. Check browser permissions or use File Upload instead.');
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (mode === 'camera') startCamera();
    else stopCamera();
    return () => stopCamera();
  }, [mode, startCamera, stopCamera]);

  const captureAndVerify = async () => {
    if (!videoRef.current || !cameraReady) return;
    setLoading(true); setError('');
    const canvas = document.createElement('canvas');
    canvas.width  = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext('2d')!.drawImage(videoRef.current, 0, 0);
    canvas.toBlob(async blob => {
      if (!blob) { setLoading(false); return; }
      const f = new File([blob], 'capture.jpg', { type: 'image/jpeg' });
      try {
        const r = await verifyPackage(f);
        setResult(r);
      } catch (e) {
        const err = e as { response?: { data?: { detail?: string } } };
        setError(err?.response?.data?.detail ?? 'Verification failed.');
      } finally { setLoading(false); }
    }, 'image/jpeg', 0.92);
  };

  const handleFile = (f: File) => {
    setFile(f);
    const url = URL.createObjectURL(f);
    setPreview(url);
  };

  const submitUpload = async () => {
    if (!file) return;
    setLoading(true); setError('');
    try {
      const r = await verifyPackage(file);
      setResult(r);
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err?.response?.data?.detail ?? 'Verification failed.');
    } finally { setLoading(false); }
  };

  const reset = () => {
    setResult(null); setMode('choose');
    setFile(null); setPreview(null); setError('');
  };

  if (result) return (
    <div>
      <div className="page-header">
        <h1><span className="gradient-text">Verification</span> Result</h1>
        <p>Two-tier check: label self-consistency and database registry lookup.</p>
      </div>
      <VerifyResult result={result} onReset={reset} />
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <h1><span className="gradient-text">Verify</span> Package</h1>
        <p>Point your camera at the <strong>entire package</strong> — the system detects any barcode or QR code on it automatically.</p>
      </div>

      {/* Mode chooser */}
      {mode === 'choose' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, maxWidth: 520 }}>
          <button
            id="mode-camera-btn"
            className="card"
            style={{ textAlign: 'center', cursor: 'pointer', border: '1px solid var(--border)', transition: 'all 0.2s' }}
            onClick={() => setMode('camera')}
            onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
          >
            <div style={{ color: 'var(--accent)', marginBottom: 12 }}><Camera size={36} /></div>
            <h3>Live Camera</h3>
            <p className="text-sm mt-2">Point at the whole package — barcodes and QR codes are located automatically.</p>
          </button>

          <button
            id="mode-upload-btn"
            className="card"
            style={{ textAlign: 'center', cursor: 'pointer', border: '1px solid var(--border)', transition: 'all 0.2s' }}
            onClick={() => setMode('upload')}
            onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
          >
            <div style={{ color: 'var(--info)', marginBottom: 12 }}><Upload size={36} /></div>
            <h3>Upload Image</h3>
            <p className="text-sm mt-2">Upload a PNG or JPG photo of the entire package (not just the code crop).</p>
          </button>
        </div>
      )}

      {/* Camera mode */}
      {mode === 'camera' && (
        <div style={{ maxWidth: 680 }}>
          <div className="flex items-center gap-2 mb-4">
            <button className="btn btn-secondary btn-sm" onClick={() => setMode('choose')}>
              <X size={14} /> Back
            </button>
            <span className="text-secondary text-sm">Point camera at the whole package — codes are detected automatically</span>
          </div>

          {cameraError ? (
            <div className="alert alert-danger">
              <CameraOff size={18} /><span>{cameraError}</span>
            </div>
          ) : (
            <>
              <div className="camera-container">
                <video ref={videoRef} playsInline muted />
                {cameraReady && (
                  <div className="camera-overlay">
                    <div className="scan-corner tl" />
                    <div className="scan-corner tr" />
                    <div className="scan-corner bl" />
                    <div className="scan-corner br" />
                    <div className="scan-line" />
                  </div>
                )}
                {!cameraReady && (
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div className="spinner" />
                  </div>
                )}
              </div>
              <button
                id="capture-btn"
                className="btn btn-primary btn-lg mt-4"
                onClick={captureAndVerify}
                disabled={!cameraReady || loading}
                style={{ width: '100%' }}
              >
                {loading ? <><div className="spinner" /> Verifying…</> : <><ScanLine size={18} /> Capture & Verify</>}
              </button>
            </>
          )}
          {error && <div className="alert alert-danger mt-3">{error}</div>}
        </div>
      )}

      {/* Upload mode */}
      {mode === 'upload' && (
        <div style={{ maxWidth: 520 }}>
          <div className="flex items-center gap-2 mb-4">
            <button className="btn btn-secondary btn-sm" onClick={() => setMode('choose')}>
              <X size={14} /> Back
            </button>
          </div>

          {preview ? (
            <div className="card mb-4">
              <div className="card-header">
                <div className="card-title"><Image size={16} /> Selected Image</div>
                <button className="btn btn-secondary btn-icon btn-sm" onClick={() => { setFile(null); setPreview(null); }}>
                  <X size={14} />
                </button>
              </div>
              <img src={preview} alt="label preview"
                style={{ width: '100%', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', maxHeight: 300, objectFit: 'contain', background: '#000' }}
              />
              <div className="text-xs text-muted mt-2">{file?.name} — {(file!.size / 1024).toFixed(1)} KB</div>
            </div>
          ) : (
            <div
              id="upload-dropzone"
              className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
              onClick={() => document.getElementById('upload-file-input')?.click()}
              style={{ cursor: 'pointer' }}
            >
              <input
                id="upload-file-input"
                type="file" accept="image/*"
                onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
                style={{ display: 'none' }}
              />
              <Upload size={36} style={{ color: 'var(--accent)', marginBottom: 12 }} />
              <h3>Drop image here</h3>
              <p className="text-sm mt-2">or click to browse — PNG, JPG, JPEG supported</p>
            </div>
          )}

          {error && <div className="alert alert-danger mb-3">{error}</div>}

          <button
            id="upload-verify-btn"
            className="btn btn-primary btn-lg w-full"
            onClick={submitUpload}
            disabled={!file || loading}
          >
            {loading ? <><div className="spinner" /> Verifying…</> : <><ScanLine size={18} /> Verify Label</>}
          </button>
        </div>
      )}
    </div>
  );
}
