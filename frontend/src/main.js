import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
const API = 'http://127.0.0.1:8000/api';
async function request(path, options = {}) { const r = await fetch(API + path, options); if (!r.ok) {
    const b = await r.json().catch(() => null);
    throw new Error(typeof b?.detail === 'string' ? b.detail : r.statusText);
} return r.json(); }
const time = (s) => s == null ? '—' : `${String(Math.floor(s / 60)).padStart(2, '0')}:${(s % 60).toFixed(2).padStart(5, '0')}`;
function App() {
    const [videos, setVideos] = useState([]), [selected, setSelected] = useState(), [file, setFile] = useState(null), [job, setJob] = useState(), [query, setQuery] = useState(''), [result, setResult] = useState(), [answer, setAnswer] = useState(), [interpreter, setInterpreter] = useState(), [suggestions, setSuggestions] = useState([]), [suggestionVideo, setSuggestionVideo] = useState(), [error, setError] = useState(''), [videoUrl, setVideoUrl] = useState(''), [evidenceUrl, setEvidenceUrl] = useState('');
    const player = useRef(null);
    const selectedRef = useRef(undefined);
    const loadVideos = () => request('/videos').then((v) => { setVideos(v); setSelected(old => old ?? v[0]?.id); }).catch(e => setError(e.message));
    const loadSuggestions = (id) => request(`/videos/${id}/events`).then(x => { if (selectedRef.current === id) {
        setSuggestions(x.suggestions || []);
        setSuggestionVideo(id);
    } }).catch(e => { if (selectedRef.current === id)
        setError(e.message); });
    useEffect(() => { loadVideos(); }, []);
    useEffect(() => { selectedRef.current = selected; if (!selected)
        return; setSuggestions([]); setSuggestionVideo(undefined); setResult(undefined); setAnswer(undefined); setEvidenceUrl(''); fetch(`${API}/videos/${selected}/file`).then(async (r) => { if (!r.ok)
        throw Error('Unable to load original video'); return URL.createObjectURL(await r.blob()); }).then(url => setVideoUrl(old => { if (old)
        URL.revokeObjectURL(old); return url; })).catch(e => setError(e.message)); loadSuggestions(selected); }, [selected]);
    const poll = (id) => { const t = window.setInterval(async () => { try {
        const x = await request(`/jobs/${id}`);
        setJob(x);
        if (['completed', 'completed_with_warnings', 'failed'].includes(x.status)) {
            clearInterval(t);
            if (x.status !== 'failed' && x.video_id)
                loadSuggestions(x.video_id);
        }
    }
    catch (e) {
        clearInterval(t);
        setError(e.message);
    } }, 1000); };
    const upload = async () => { if (!file)
        return; try {
        const body = new FormData();
        body.append('file', file);
        const v = await request('/videos/upload', { method: 'POST', body });
        selectedRef.current = v.id;
        setSelected(v.id);
        setSuggestions([]);
        const j = await request(`/videos/${v.id}/process`, { method: 'POST' });
        setJob(j);
        poll(j.job_id);
        loadVideos();
    }
    catch (e) {
        setError(e.message);
    } };
    const search = async (text = query) => { if (!text.trim())
        return; try {
        const x = await request('/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: text, video_id: selected }) });
        setQuery(text);
        setResult(x.primary_evidence || null);
        setAnswer(x.answer);
        setInterpreter(x.query_interpreter);
        setError('');
    }
    catch (e) {
        setError(e.message);
    } };
    const openEvidence = async () => { if (!result)
        return; try {
        const params = new URLSearchParams();
        if (result.track_id != null)
            params.set('track_id', String(result.track_id));
        if (result.matched_object_id != null)
            params.set('object_id', String(result.matched_object_id));
        const response = await fetch(API + (result.frame_url || `/frames/${result.evidence_frame_id}/evidence?${params}`));
        if (!response.ok)
            throw Error('Evidence frame could not be loaded.');
        const url = URL.createObjectURL(await response.blob());
        setEvidenceUrl(old => { if (old)
            URL.revokeObjectURL(old); return url; });
        if (player.current) {
            player.current.currentTime = result.evidence_timestamp;
            player.current.play().catch(() => undefined);
        }
    }
    catch (e) {
        setError(e.message);
    } };
    const stages = [['opening_video', 'Video validated'], ['detection_and_tracking', 'YOLOv8 + ByteTrack + objects'], ['indexing_tracks', 'Evidence indexed'], ['attributes', 'Qwen3-VL attributes'], ['action_recognition', 'VideoMAE actions'], ['complete', 'Processing complete']];
    const stageIndex = stages.findIndex(s => s[0] === job?.stage);
    return _jsxs("main", { children: [_jsxs("header", { children: [_jsxs("div", { children: [_jsx("b", { children: "CCTV FORENSIC SEARCH" }), _jsx("span", { children: "Evidence-backed video investigation" })] }), _jsx("span", { className: "muted", children: "Local investigation workspace" })] }), _jsxs("section", { className: "hero", children: [_jsx("h1", { children: "Ask questions about the video." }), _jsx("p", { children: "Answers are grounded in indexed CCTV evidence." })] }), _jsxs("section", { className: "workspace", children: [_jsxs("article", { className: "reference", children: [_jsx("h2", { children: "Original CCTV video" }), videos.length ? _jsxs(_Fragment, { children: [_jsx("select", { value: selected, onChange: e => setSelected(Number(e.target.value)), children: videos.map(v => _jsx("option", { value: v.id, children: v.filename }, v.id)) }), videoUrl && _jsx("video", { ref: player, src: videoUrl, controls: true }), _jsxs("p", { className: "muted", children: ["Duration: ", time(videos.find(v => v.id === selected)?.duration)] })] }) : _jsx("p", { children: "Upload CCTV footage to begin." })] }), _jsxs("article", { children: [_jsx("h2", { children: "Upload & processing" }), _jsx("input", { type: "file", accept: "video/mp4,video/avi,video/quicktime", onChange: e => setFile(e.target.files?.[0] || null) }), _jsx("button", { onClick: upload, children: "Upload & Process" }), job && _jsxs("div", { className: "status", children: [_jsx("b", { children: job.status === 'completed_with_warnings' ? 'Completed with warnings' : job.status }), _jsx("div", { className: "bar", children: _jsx("i", { style: { width: `${job.progress || 0}%` } }) }), _jsxs("small", { children: [Math.round(job.progress || 0), "% \u2014 ", job.detail] }), _jsx("div", { className: "stages", children: stages.map((s, i) => _jsxs("small", { className: job.status === 'failed' ? '' : (job.status.startsWith('completed') || i <= stageIndex ? 'done' : ''), children: [job.status.startsWith('completed') || i <= stageIndex ? '✓' : '○', " ", s[1]] }, s[0])) }), job.error && _jsx("small", { className: "warn", children: job.error })] })] })] }), _jsxs("section", { className: "search", children: [_jsx("h2", { children: "Search this video" }), _jsx("textarea", { placeholder: "Ask a question about the video\u2026", value: query, onChange: e => setQuery(e.target.value), onKeyDown: e => { if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            search();
                        } } }), _jsx("button", { disabled: !selected || !query.trim(), onClick: () => search(), children: "Ask" }), _jsx("h3", { children: "Suggested searches" }), suggestionVideo === selected && suggestions.length ? _jsx("div", { className: "suggestions", children: suggestions.map(s => _jsx("button", { className: "secondary", onClick: () => search(s.query), children: s.title }, s.query)) }) : _jsx("p", { className: "muted", children: "Suggestions appear after this video is fully analysed." })] }), result !== undefined && _jsxs("section", { className: "search", children: [_jsx("h2", { children: "Answer" }), _jsxs("article", { className: "result", children: [_jsx("p", { children: answer?.text || 'No verified evidence found for this query.' }), _jsx("small", { className: "muted", children: answer?.provider === 'gemini' ? 'Gemini answer grounded in local evidence' : 'Answer from indexed evidence' })] }), interpreter && _jsxs("p", { className: "muted", children: ["Query interpretation: ", interpreter.used ? 'Gemini LLM' : 'local rules', interpreter.reason ? ` — ${interpreter.reason}` : ''] }), result && _jsxs("article", { className: "result", children: [_jsxs("h3", { children: ["Supporting evidence", _jsxs("em", { children: ["confidence ", result.confidence.toFixed(2)] })] }), _jsxs("div", { className: "eventTime", children: [_jsx("b", { children: time(result.evidence_timestamp) }), _jsxs("small", { children: ["Evidence: ", time(result.evidence_start), " \u2192 ", time(result.evidence_end), " \u00B7 ", result.video?.filename] })] }), _jsx("p", { children: result.match_reasons.map(x => _jsxs("span", { className: "tag", children: ["\u2713 ", x] }, x)) }), _jsx("button", { onClick: openEvidence, children: "View evidence" })] })] }), evidenceUrl && _jsxs("section", { className: "evidence", children: [_jsxs("h2", { children: ["Evidence frame \u2014 ", time(result?.evidence_timestamp)] }), _jsx("img", { src: evidenceUrl, alt: "CCTV evidence frame" })] }), error && _jsx("p", { className: "error", children: error })] });
}
createRoot(document.getElementById('root')).render(_jsx(App, {}));
