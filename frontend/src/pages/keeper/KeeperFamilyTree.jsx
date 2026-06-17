import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  createRelationship,
  createTreeMember,
  deleteTreeMember,
  getMemberStories,
  getTree,
  updateTreeMember,
} from '../../api/keeperClient';
import { useKeeper } from './KeeperContext';

// ── Layout constants ───────────────────────────────────────────
const NODE_W = 152;
const NODE_H = 72;
const GAP_X = 36;
const GAP_Y = 58; // gap between generation rows (centre-to-centre = NODE_H + GAP_Y)
const ROW_H = NODE_H + GAP_Y;
const RING_R = 90; // action ring radius
const CANVAS_PAD = 60;

// ── Grid helpers ───────────────────────────────────────────────
function slotToPixel(col, row) {
  return {
    x: CANVAS_PAD + col * (NODE_W + GAP_X),
    y: CANVAS_PAD + row * ROW_H,
  };
}

function snapToSlot(pixelX, pixelY) {
  return {
    col: Math.max(0, Math.round((pixelX - CANVAS_PAD) / (NODE_W + GAP_X))),
    row: Math.max(0, Math.round((pixelY - CANVAS_PAD) / ROW_H)),
  };
}

// ── Adjacency builder ──────────────────────────────────────────
function buildAdjacency(placed, relationships) {
  const placedIds = new Set(placed.map((m) => m.id));
  const childrenOf = {};
  const parentsOf = {};
  const spousesOf = {};
  for (const m of placed) {
    childrenOf[m.id] = [];
    parentsOf[m.id] = [];
    spousesOf[m.id] = [];
  }
  for (const r of relationships) {
    if (!placedIds.has(r.member_id) || !placedIds.has(r.related_member_id)) continue;
    if (r.relationship_type === 'child') {
      childrenOf[r.member_id].push(r.related_member_id);
      if (!parentsOf[r.related_member_id].includes(r.member_id)) {
        parentsOf[r.related_member_id].push(r.member_id);
      }
    }
    if (r.relationship_type === 'spouse') {
      if (!spousesOf[r.member_id].includes(r.related_member_id)) {
        spousesOf[r.member_id].push(r.related_member_id);
      }
    }
  }
  return { childrenOf, parentsOf, spousesOf };
}

// ── Generation levels (BFS) ────────────────────────────────────
function computeGenerations(placed, relationships) {
  const { childrenOf, parentsOf, spousesOf } = buildAdjacency(placed, relationships);
  const level = {};
  const queue = [];
  for (const m of placed) {
    if (!parentsOf[m.id] || parentsOf[m.id].length === 0) {
      level[m.id] = 0;
      queue.push(m.id);
    }
  }
  if (queue.length === 0 && placed.length > 0) {
    level[placed[0].id] = 0;
    queue.push(placed[0].id);
  }
  const visited = new Set(queue);
  let qi = 0;
  while (qi < queue.length) {
    const id = queue[qi++];
    for (const childId of (childrenOf[id] || [])) {
      if (!visited.has(childId)) {
        visited.add(childId);
        level[childId] = (level[id] || 0) + 1;
        queue.push(childId);
      }
    }
    for (const spouseId of (spousesOf[id] || [])) {
      if (!visited.has(spouseId)) {
        visited.add(spouseId);
        level[spouseId] = level[id] || 0;
        queue.push(spouseId);
      }
    }
  }
  for (const m of placed) {
    if (level[m.id] === undefined) level[m.id] = 0;
  }
  return level;
}

// ── Auto slot assignment ───────────────────────────────────────
// Returns { [memberId]: { col, row } } for the default layout.
function computeAutoSlots(placed, relationships) {
  if (!placed.length) return {};
  const { parentsOf, spousesOf } = buildAdjacency(placed, relationships);
  const level = computeGenerations(placed, relationships);

  const levels = {};
  for (const m of placed) {
    const l = level[m.id] ?? 0;
    if (!levels[l]) levels[l] = [];
    levels[l].push(m.id);
  }
  const maxLevel = Math.max(...Object.keys(levels).map(Number));

  const slots = {};
  const assignedAtLevel = {};

  for (let l = 0; l <= maxLevel; l++) {
    const ids = levels[l] || [];
    const ordered = [];
    const seen = new Set();
    for (const id of ids) {
      if (seen.has(id)) continue;
      seen.add(id);
      ordered.push(id);
      for (const spouseId of (spousesOf[id] || [])) {
        if (!seen.has(spouseId) && ids.includes(spouseId)) {
          seen.add(spouseId);
          ordered.push(spouseId);
        }
      }
    }
    assignedAtLevel[l] = ordered;

    // Try to centre children under their parents from the row above
    let startCol = 0;
    if (l > 0 && assignedAtLevel[l - 1]) {
      const parents = assignedAtLevel[l - 1];
      const relevantParents = parents.filter((pid) =>
        ordered.some((cid) => parentsOf[cid]?.includes(pid))
      );
      if (relevantParents.length > 0) {
        const minParentCol = Math.min(...relevantParents.map((pid) => slots[pid]?.col ?? 0));
        const maxParentCol = Math.max(...relevantParents.map((pid) => slots[pid]?.col ?? 0));
        const parentCentreX =
          CANVAS_PAD + ((minParentCol + maxParentCol) * (NODE_W + GAP_X)) / 2 + NODE_W / 2;
        const totalW = ordered.length * NODE_W + (ordered.length - 1) * GAP_X;
        const startX = Math.max(CANVAS_PAD, parentCentreX - totalW / 2);
        startCol = Math.max(0, Math.round((startX - CANVAS_PAD) / (NODE_W + GAP_X)));
      }
    }

    for (let i = 0; i < ordered.length; i++) {
      slots[ordered[i]] = { col: startCol + i, row: l };
    }
  }

  return slots;
}

// ── Connector paths from pixel positions ───────────────────────
function computeConnectors(placed, relationships, pixelPositions) {
  const { childrenOf, spousesOf } = buildAdjacency(placed, relationships);
  const connectors = [];
  const drawnCouples = new Set();

  for (const m of placed) {
    const id = m.id;
    const pos = pixelPositions[id];
    if (!pos) continue;

    // Spouse connector
    for (const spouseId of (spousesOf[id] || [])) {
      const pairKey = [id, spouseId].sort().join('-');
      const spos = pixelPositions[spouseId];
      if (!drawnCouples.has(pairKey) && spos) {
        drawnCouples.add(pairKey);
        // Connect nearest horizontal edges
        let x1, x2;
        if (pos.x + NODE_W <= spos.x) {
          x1 = pos.x + NODE_W;
          x2 = spos.x;
        } else if (spos.x + NODE_W <= pos.x) {
          x1 = spos.x + NODE_W;
          x2 = pos.x;
        } else {
          x1 = pos.x + NODE_W / 2;
          x2 = spos.x + NODE_W / 2;
        }
        const y1 = pos.y + NODE_H / 2;
        const y2 = spos.y + NODE_H / 2;
        connectors.push({ type: 'couple', x1, y1, x2, y2, mx: (x1 + x2) / 2, my: (y1 + y2) / 2 });
      }
    }

    // Children connector
    const children = (childrenOf[id] || []).filter((cid) => pixelPositions[cid]);
    if (children.length === 0) continue;

    let stemX = pos.x + NODE_W / 2;
    const mySpouses = (spousesOf[id] || []).filter((sid) => pixelPositions[sid]);
    if (mySpouses.length > 0) {
      const spouseId = mySpouses[0];
      const spos = pixelPositions[spouseId];
      if (pos.x > spos.x) continue; // let the left spouse draw it
      stemX = (pos.x + NODE_W + spos.x) / 2;
    }
    const stemY1 = pos.y + NODE_H;
    const stemY2 = pos.y + NODE_H + GAP_Y / 2;

    const childXCentres = children.map((cid) => pixelPositions[cid].x + NODE_W / 2);
    connectors.push({
      type: 'children',
      stemX,
      stemY1,
      stemY2,
      barX1: Math.min(...childXCentres),
      barX2: Math.max(...childXCentres),
      childDrops: children.map((cid) => ({
        x: pixelPositions[cid].x + NODE_W / 2,
        y1: stemY2,
        y2: pixelPositions[cid].y,
      })),
    });
  }
  return connectors;
}

// ── Helpers ────────────────────────────────────────────────────
function deceasedSuffix(m) {
  if (!m.is_deceased) return null;
  return <span className="tree-dagger">†</span>;
}

function memberMetaStr(m) {
  const parts = [];
  if (m.birth_year) parts.push(`b. ${m.birth_year}`);
  return parts.join(' · ') || null;
}

const REL_LABELS = { parent: 'Parent', child: 'Child', spouse: 'Spouse', sibling: 'Sibling' };
const REL_OPPOSITE = { parent: 'child', child: 'parent', spouse: 'spouse', sibling: 'sibling' };

// ── Sub-components ─────────────────────────────────────────────

function UnplacedSidebar({ unplaced, onChipClick }) {
  return (
    <div className="tree-unplaced">
      <div className="tree-unplaced-header">
        <span className="tree-unplaced-label">Unplaced members</span>
        <span className="tree-unplaced-count">{unplaced.length}</span>
      </div>
      <div className="tree-unplaced-hint">
        From story mentions. Click to connect.
      </div>
      <div className="tree-unplaced-list">
        {unplaced.length === 0 && (
          <div className="tree-unplaced-empty">All members placed</div>
        )}
        {unplaced.map((m) => (
          <button
            key={m.id}
            type="button"
            className="tree-unplaced-chip"
            onClick={() => onChipClick(m)}
          >
            <div className="tree-chip-avatar" />
            <div style={{ minWidth: 0 }}>
              <div className="tree-chip-name">
                {m.name_en}
                {m.is_deceased && <span className="tree-dagger">†</span>}
              </div>
              {m.name_kh && <div className="tree-chip-name-kh">{m.name_kh}</div>}
            </div>
          </button>
        ))}
      </div>
      <div className="tree-gen-legend">
        <div className="tree-gen-legend-label">Generations</div>
        {['Grandparents', 'Parents', 'Children'].map((label, i) => (
          <div key={label} className="tree-gen-legend-row">
            <span className={`tree-gen-swatch tree-gen-swatch-${i}`} />
            <span className="tree-gen-legend-text">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TreeNode({ node, isSelected, isDragging, onMouseDown }) {
  const { member, x, y, gen } = node;
  const genClass = `tree-node-gen-${Math.min(gen, 4)}`;
  return (
    <div
      className={`tree-node ${genClass} ${isSelected ? 'selected' : ''} ${isDragging ? 'is-dragging' : ''}`}
      style={{ left: x, top: y, height: NODE_H }}
      onMouseDown={(e) => onMouseDown(e, member.id)}
    >
      <div className="tree-node-avatar" />
      <div className="tree-node-info">
        <div className="tree-node-name">
          {member.name_en}
          {deceasedSuffix(member)}
        </div>
        {member.name_kh && <div className="tree-node-name-kh">{member.name_kh}</div>}
        {memberMetaStr(member) && (
          <div className="tree-node-meta">{memberMetaStr(member)}</div>
        )}
      </div>
    </div>
  );
}

function ConnectorSVG({ connectors, canvasW, canvasH }) {
  const strokeProps = { stroke: 'rgba(42,38,32,0.24)', strokeWidth: 2, fill: 'none' };
  return (
    <svg
      className="tree-svg"
      width={canvasW}
      height={canvasH}
      style={{ width: canvasW, height: canvasH }}
    >
      {connectors.map((c, i) => {
        if (c.type === 'couple') {
          return (
            <g key={i}>
              <line x1={c.x1} y1={c.y1} x2={c.x2} y2={c.y2} {...strokeProps} />
              <circle cx={c.mx} cy={c.my} r={4} fill="#e8d3bf" stroke="rgba(163,98,62,0.4)" strokeWidth={1} />
            </g>
          );
        }
        if (c.type === 'children') {
          return (
            <g key={i}>
              {/* Vertical stem from couple midpoint down */}
              <line x1={c.stemX} y1={c.stemY1} x2={c.stemX} y2={c.stemY2} {...strokeProps} />
              {/* Horizontal bar spanning children */}
              {c.barX1 !== c.barX2 && (
                <line x1={c.barX1} y1={c.stemY2} x2={c.barX2} y2={c.stemY2} {...strokeProps} />
              )}
              {/* Vertical drops to each child */}
              {c.childDrops.map((d, j) => (
                <line key={j} x1={d.x} y1={d.y1} x2={d.x} y2={d.y2} {...strokeProps} />
              ))}
            </g>
          );
        }
        return null;
      })}
    </svg>
  );
}

function NodeActionRing({ node, onAdd }) {
  const { x, y } = node;
  const cx = x + NODE_W / 2;
  const cy = y + NODE_H / 2;
  const left = cx - RING_R - 16;
  const top = cy - RING_R - 16;
  const size = (RING_R + 16) * 2;

  const buttons = [
    { rel: 'parent',  bx: cx - 16, by: cy - RING_R - 16, label: 'Parent',  labelX: cx, labelY: cy - RING_R - 32, labelAnchor: 'center' },
    { rel: 'child',   bx: cx - 16, by: cy + RING_R - 16, label: 'Child',   labelX: cx, labelY: cy + RING_R + 30, labelAnchor: 'center' },
    { rel: 'spouse',  bx: cx + RING_R - 16, by: cy - 16, label: 'Spouse',  labelX: cx + RING_R + 36, labelY: cy - 6, labelAnchor: 'left' },
    { rel: 'sibling', bx: cx - RING_R - 16, by: cy - 16, label: 'Sibling', labelX: cx - RING_R - 46, labelY: cy - 6, labelAnchor: 'right' },
  ];

  return (
    <div
      className="tree-action-ring"
      style={{ left, top, width: size, height: size, pointerEvents: 'none' }}
    >
      <div
        className="tree-action-ring-circle"
        style={{
          left: 16,
          top: 16,
          width: RING_R * 2,
          height: RING_R * 2,
        }}
      />
      {buttons.map(({ rel, bx, by, label, labelX, labelY, labelAnchor }) => (
        <div key={rel} style={{ position: 'absolute', left: 0, top: 0, pointerEvents: 'none' }}>
          <button
            type="button"
            className="tree-ring-btn"
            style={{ position: 'absolute', left: bx - left, top: by - top }}
            onClick={(e) => { e.stopPropagation(); onAdd(rel); }}
          >
            +
          </button>
          <span
            className="tree-ring-label"
            style={{
              position: 'absolute',
              left: labelAnchor === 'center'
                ? labelX - left - 20
                : labelAnchor === 'left'
                ? labelX - left
                : undefined,
              right: labelAnchor === 'right' ? size - (labelX - left) : undefined,
              top: labelY - top,
            }}
          >
            {label}
          </span>
        </div>
      ))}
    </div>
  );
}

function ProfilePanel({ member, stories, loading, onClose, onAddRelationship, onEdit, onDelete }) {
  const navigate = useNavigate();
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  async function handleDelete() {
    setDeleting(true);
    setDeleteError('');
    try {
      await onDelete();
    } catch (e) {
      setDeleteError(e.message || 'Failed to remove member');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="tree-profile">
      <div className="tree-profile-scroll">
        <div className="tree-profile-top">
          <span className="tree-profile-eyebrow">Member</span>
          <div className="tree-profile-top-actions">
            <button type="button" className="tree-profile-edit-btn" onClick={onEdit}>Edit</button>
            <button type="button" className="tree-profile-close" onClick={onClose}>×</button>
          </div>
        </div>
        <div className="tree-profile-identity">
          <div className="tree-profile-avatar" />
          <div>
            <div className="tree-profile-name">
              {member.name_en}
              {deceasedSuffix(member)}
            </div>
            {member.name_kh && (
              <div className="tree-profile-name-kh">{member.name_kh}</div>
            )}
          </div>
        </div>
        {memberMetaStr(member) && (
          <div className="tree-profile-meta">{memberMetaStr(member)}</div>
        )}
        {member.notes && (
          <div className="tree-profile-bio">{member.notes}</div>
        )}

        <div className="tree-profile-divider" />

        <div className="tree-profile-section-label">
          {loading
            ? 'Loading stories…'
            : `Mentioned in ${stories.length} stor${stories.length === 1 ? 'y' : 'ies'}`}
        </div>
        {stories.map((s) => (
          <button
            key={s.id}
            type="button"
            className="tree-profile-story"
            onClick={() => navigate(`/keeper/story/${s.id}`)}
          >
            <div className="tree-profile-story-dot" />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="tree-profile-story-title">
                {s.title_en || s.title_kh || 'Untitled'}
              </div>
              {s.narrator_name_raw && (
                <div className="tree-profile-story-meta">{s.narrator_name_raw}</div>
              )}
            </div>
            <span className="tree-profile-story-arrow">›</span>
          </button>
        ))}

        <div className="tree-profile-add-label">Add relationship</div>
        <div className="tree-profile-add-grid">
          {['parent', 'child', 'spouse', 'sibling'].map((rel) => (
            <button
              key={rel}
              type="button"
              className="tree-profile-add-btn"
              onClick={() => onAddRelationship(rel)}
            >
              + {REL_LABELS[rel]}
            </button>
          ))}
        </div>

        <div className="tree-profile-divider" />

        {!deleteConfirm ? (
          <button
            type="button"
            className="tree-profile-remove-btn"
            onClick={() => setDeleteConfirm(true)}
          >
            Remove from tree
          </button>
        ) : (
          <div className="tree-delete-confirm">
            <div className="tree-delete-confirm-text">
              Remove <strong>{member.name_en}</strong> from the family tree?
            </div>
            {deleteError && (
              <div style={{ marginBottom: 10, fontSize: 12, color: 'var(--danger)' }}>{deleteError}</div>
            )}
            <div className="tree-delete-confirm-btns">
              <button type="button" className="tree-btn-secondary" onClick={() => { setDeleteConfirm(false); setDeleteError(''); }} disabled={deleting}>Cancel</button>
              <button type="button" className="tree-btn-danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? 'Removing…' : 'Remove'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Add Member Drawer ──────────────────────────────────────────
const GENDER_OPTIONS = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
  { value: 'unknown', label: 'Unknown' },
];

function AddMemberDrawer({ anchor, relationship, allMembers, placed, onClose, onSaved, onLink }) {
  // mode: 'new' | 'link-step1' | 'link-step2'
  const [mode, setMode] = useState('new');
  const [form, setForm] = useState({
    name_en: '', name_kh: '', gender: null, birth_year: '', is_deceased: false,
    deceased_year: '', notes: '',
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLinkMember, setSelectedLinkMember] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const { token } = useKeeper();

  const anchorName = anchor?.name_en || '';
  const relLabel = relationship ? REL_LABELS[relationship] : '';

  const headerEyebrow = anchor
    ? `Add ${relLabel.toLowerCase()}`
    : 'Add first member';
  const headerTitle = anchor ? `for ${anchorName}` : 'Start your family tree';

  function handleField(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleSaveNew() {
    if (!form.name_en.trim()) { setError('Name (EN) is required'); return; }
    setSaving(true);
    setError('');
    try {
      const payload = {
        name_en: form.name_en.trim(),
        name_kh: form.name_kh.trim() || null,
        gender: form.gender || null,
        birth_year: form.birth_year ? parseInt(form.birth_year, 10) : null,
        is_deceased: form.is_deceased,
        notes: form.notes.trim() || null,
        anchor_member_id: anchor?.id || null,
        relationship_type: relationship || null,
      };
      const newMember = await createTreeMember(token, payload);
      onSaved(newMember);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleConfirmLink() {
    if (!selectedLinkMember) return;
    setSaving(true);
    setError('');
    try {
      if (anchor) {
        await onLink(selectedLinkMember, relationship);
      } else {
        // No anchor — just mark the member as a tree root
        await createTreeMember(token, {
          name_en: selectedLinkMember.name_en,
          name_kh: selectedLinkMember.name_kh,
          gender: selectedLinkMember.gender,
          birth_year: selectedLinkMember.birth_year,
          is_deceased: selectedLinkMember.is_deceased,
          notes: selectedLinkMember.notes,
        });
        onSaved(selectedLinkMember);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  // Filter members for search
  const lowerQ = searchQuery.toLowerCase();
  const filteredUnplaced = allMembers
    .filter((m) => !placed.find((p) => p.id === m.id))
    .filter((m) => !lowerQ || m.name_en.toLowerCase().includes(lowerQ) || (m.name_kh || '').includes(lowerQ));
  const filteredAll = allMembers.filter(
    (m) => !lowerQ || m.name_en.toLowerCase().includes(lowerQ) || (m.name_kh || '').includes(lowerQ)
  );

  const linkTargetInStories = selectedLinkMember
    ? (selectedLinkMember.story_count || 0) > 0
    : false;

  return (
    <>
      <div className="tree-drawer-backdrop" onClick={onClose} />
      <div className="tree-drawer">
        <div className="tree-drawer-header">
          <div>
            {mode !== 'new' && (
              <div className="tree-step-indicator">
                Step {mode === 'link-step1' ? '1' : '2'} of 2
              </div>
            )}
            <div className="tree-drawer-eyebrow">{headerEyebrow}</div>
            <div className="tree-drawer-title">
              {mode === 'new' ? headerTitle : mode === 'link-step1' ? 'Link an existing member' : 'Confirm link'}
            </div>
          </div>
          <button type="button" className="tree-drawer-close" onClick={onClose}>×</button>
        </div>

        <div className="tree-drawer-body">
          {error && (
            <div style={{ marginBottom: 14, padding: '9px 12px', background: 'var(--danger-bg)', border: '1px solid var(--danger-border)', borderRadius: 9, font: '400 12.5px/1.5 var(--font-sans)', color: 'var(--danger)' }}>
              {error}
            </div>
          )}

          {mode === 'new' && (
            <>
              {anchor && (
                <button type="button" className="tree-link-shortcut" onClick={() => setMode('link-step1')}>
                  ↩ Link to an existing family member instead
                </button>
              )}

              <div className="tree-field-group">
                <div className="tree-field-label">Name (EN) <span className="tree-field-required">*</span></div>
                <input
                  className="tree-field-input"
                  placeholder="e.g. Sophea Roeung"
                  value={form.name_en}
                  onChange={(e) => handleField('name_en', e.target.value)}
                />
              </div>

              <div className="tree-field-group">
                <div className="tree-field-label">Name (KH)</div>
                <input
                  className="tree-field-input kh"
                  placeholder="ឈ្មោះជាភាសាខ្មែរ"
                  value={form.name_kh}
                  onChange={(e) => handleField('name_kh', e.target.value)}
                />
              </div>

              <div className="tree-field-group">
                <div className="tree-field-label">Gender</div>
                <div className="tree-gender-row">
                  {GENDER_OPTIONS.map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      className={`tree-gender-btn ${form.gender === value ? 'active' : ''}`}
                      onClick={() => handleField('gender', form.gender === value ? null : value)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="tree-field-group">
                <div className="tree-field-label">Birth year</div>
                <input
                  className="tree-field-input"
                  placeholder="e.g. 1938"
                  value={form.birth_year}
                  onChange={(e) => handleField('birth_year', e.target.value.replace(/\D/g, ''))}
                  inputMode="numeric"
                />
              </div>

              <button
                type="button"
                className="tree-deceased-toggle"
                onClick={() => handleField('is_deceased', !form.is_deceased)}
              >
                <div>
                  <div className="tree-deceased-toggle-label">Deceased</div>
                  <div className="tree-deceased-toggle-sub">Adds a death year and a † marker</div>
                </div>
                <div className={`tree-toggle-track ${form.is_deceased ? 'on' : ''}`}>
                  <div className="tree-toggle-thumb" />
                </div>
              </button>

              {form.is_deceased && (
                <div className="tree-field-group">
                  <div className="tree-field-label">Death year</div>
                  <input
                    className="tree-field-input"
                    placeholder="e.g. 1998"
                    value={form.deceased_year}
                    onChange={(e) => handleField('deceased_year', e.target.value.replace(/\D/g, ''))}
                    inputMode="numeric"
                  />
                </div>
              )}

              <div className="tree-field-group">
                <div className="tree-field-label">Short bio</div>
                <textarea
                  className="tree-field-input"
                  placeholder="1–2 sentences shown in the family book"
                  rows={3}
                  value={form.notes}
                  onChange={(e) => handleField('notes', e.target.value)}
                  style={{ resize: 'vertical', lineHeight: 1.5 }}
                />
              </div>
            </>
          )}

          {mode === 'link-step1' && (
            <>
              <div className="tree-search-input-wrap">
                <span className="tree-search-icon">⌕</span>
                <input
                  className="tree-search-input"
                  placeholder="Search by name"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  autoFocus
                />
              </div>

              {filteredUnplaced.length > 0 && (
                <>
                  <div className="tree-search-section-label">Unplaced members</div>
                  {filteredUnplaced.map((m) => (
                    <div
                      key={m.id}
                      className={`tree-search-result ${selectedLinkMember?.id === m.id ? 'selected-result' : ''}`}
                      onClick={() => setSelectedLinkMember(m)}
                    >
                      <div className="tree-search-result-avatar" />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="tree-search-result-name">{m.name_en}{m.is_deceased && <span className="tree-dagger">†</span>}</div>
                        {m.name_kh && <div className="tree-search-result-kh">{m.name_kh}</div>}
                      </div>
                      {selectedLinkMember?.id === m.id && <span className="tree-search-result-check">✓</span>}
                    </div>
                  ))}
                  <div style={{ height: 16 }} />
                </>
              )}

              <div className="tree-search-section-label">All family members</div>
              {filteredAll.map((m) => {
                const isPlaced = !!placed.find((p) => p.id === m.id);
                return (
                  <div
                    key={m.id}
                    className={`tree-search-result ${selectedLinkMember?.id === m.id ? 'selected-result' : ''}`}
                    onClick={() => setSelectedLinkMember(m)}
                  >
                    <div className="tree-search-result-avatar" />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="tree-search-result-name">{m.name_en}{m.is_deceased && <span className="tree-dagger">†</span>}</div>
                      {m.name_kh && <div className="tree-search-result-kh">{m.name_kh}</div>}
                    </div>
                    {isPlaced && (
                      <span className="tree-search-result-badge">already in tree</span>
                    )}
                    {selectedLinkMember?.id === m.id && !isPlaced && (
                      <span className="tree-search-result-check">✓</span>
                    )}
                  </div>
                );
              })}
            </>
          )}

          {mode === 'link-step2' && selectedLinkMember && anchor && (
            <>
              <div className="tree-confirm-sentence">
                <strong>{selectedLinkMember.name_en}</strong> will become the{' '}
                <span className="rel-word">{relLabel.toLowerCase()}</span> of{' '}
                <strong>{anchorName}</strong>.
              </div>

              <div className="tree-confirm-pair">
                <div className="tree-confirm-card">
                  <div className="tree-confirm-card-avatar" />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ font: '600 12px/1.2 var(--font-sans)', color: 'var(--ink)' }}>{selectedLinkMember.name_en}</div>
                    {selectedLinkMember.name_kh && <div style={{ font: '400 10px/1.2 var(--font-kh)', color: 'var(--clay)', marginTop: 1 }}>{selectedLinkMember.name_kh}</div>}
                  </div>
                </div>
                <div className="tree-confirm-arrow">
                  <span className="tree-confirm-arrow-label">{relLabel.toLowerCase()} of</span>
                  <span className="tree-confirm-arrow-icon">→</span>
                </div>
                <div className="tree-confirm-card">
                  <div className="tree-confirm-card-avatar" />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ font: '600 12px/1.2 var(--font-sans)', color: 'var(--ink)' }}>{anchor.name_en}</div>
                    {anchor.name_kh && <div style={{ font: '400 10px/1.2 var(--font-kh)', color: 'var(--clay)', marginTop: 1 }}>{anchor.name_kh}</div>}
                  </div>
                </div>
              </div>

              {linkTargetInStories && (
                <div className="tree-confirm-warning">
                  <span className="tree-confirm-warning-icon">ℹ</span>
                  <div className="tree-confirm-warning-text">
                    {selectedLinkMember.name_en} is mentioned in stories. Those story tags will now link to their profile in the family tree.
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="tree-drawer-footer">
          {mode === 'new' && (
            <>
              <button type="button" className="tree-btn-secondary" onClick={onClose}>Cancel</button>
              <button type="button" className="tree-btn-primary" onClick={handleSaveNew} disabled={saving}>
                {saving ? 'Adding…' : 'Add to tree'}
              </button>
            </>
          )}
          {mode === 'link-step1' && (
            <>
              <button type="button" className="tree-btn-secondary" onClick={() => setMode('new')}>Back</button>
              <button
                type="button"
                className="tree-btn-primary"
                disabled={!selectedLinkMember}
                onClick={() => setMode('link-step2')}
              >
                Continue →
              </button>
            </>
          )}
          {mode === 'link-step2' && (
            <>
              <button type="button" className="tree-btn-secondary" onClick={() => setMode('link-step1')}>Back</button>
              <button type="button" className="tree-btn-primary" onClick={handleConfirmLink} disabled={saving}>
                {saving ? 'Linking…' : 'Confirm link'}
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
}

// ── Edit Member Drawer ─────────────────────────────────────────
function EditMemberDrawer({ member, onClose, onSaved }) {
  const { token } = useKeeper();
  const [form, setForm] = useState({
    name_en: member.name_en || '',
    name_kh: member.name_kh || '',
    gender: member.gender || null,
    birth_year: member.birth_year ? String(member.birth_year) : '',
    is_deceased: member.is_deceased || false,
    notes: member.notes || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function handleField(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleSave() {
    if (!form.name_en.trim()) { setError('Name (EN) is required'); return; }
    setSaving(true);
    setError('');
    try {
      const payload = {
        name_en: form.name_en.trim(),
        name_kh: form.name_kh.trim() || null,
        gender: form.gender || null,
        birth_year: form.birth_year ? parseInt(form.birth_year, 10) : null,
        is_deceased: form.is_deceased,
        notes: form.notes.trim() || null,
      };
      const updated = await updateTreeMember(token, member.id, payload);
      onSaved(updated);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="tree-drawer-backdrop" onClick={onClose} />
      <div className="tree-drawer">
        <div className="tree-drawer-header">
          <div>
            <div className="tree-drawer-eyebrow">Edit member</div>
            <div className="tree-drawer-title">{member.name_en}</div>
          </div>
          <button type="button" className="tree-drawer-close" onClick={onClose}>×</button>
        </div>

        <div className="tree-drawer-body">
          {error && (
            <div style={{ marginBottom: 14, padding: '9px 12px', background: 'var(--danger-bg)', border: '1px solid var(--danger-border)', borderRadius: 9, font: '400 12.5px/1.5 var(--font-sans)', color: 'var(--danger)' }}>
              {error}
            </div>
          )}

          <div className="tree-field-group">
            <div className="tree-field-label">Name (EN) <span className="tree-field-required">*</span></div>
            <input
              className="tree-field-input"
              value={form.name_en}
              onChange={(e) => handleField('name_en', e.target.value)}
            />
          </div>

          <div className="tree-field-group">
            <div className="tree-field-label">Name (KH)</div>
            <input
              className="tree-field-input kh"
              placeholder="ឈ្មោះជាភាសាខ្មែរ"
              value={form.name_kh}
              onChange={(e) => handleField('name_kh', e.target.value)}
            />
          </div>

          <div className="tree-field-group">
            <div className="tree-field-label">Gender</div>
            <div className="tree-gender-row">
              {GENDER_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  className={`tree-gender-btn ${form.gender === value ? 'active' : ''}`}
                  onClick={() => handleField('gender', form.gender === value ? null : value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="tree-field-group">
            <div className="tree-field-label">Birth year</div>
            <input
              className="tree-field-input"
              placeholder="e.g. 1938"
              value={form.birth_year}
              onChange={(e) => handleField('birth_year', e.target.value.replace(/\D/g, ''))}
              inputMode="numeric"
            />
          </div>

          <button
            type="button"
            className="tree-deceased-toggle"
            onClick={() => handleField('is_deceased', !form.is_deceased)}
          >
            <div>
              <div className="tree-deceased-toggle-label">Deceased</div>
              <div className="tree-deceased-toggle-sub">Adds a † marker</div>
            </div>
            <div className={`tree-toggle-track ${form.is_deceased ? 'on' : ''}`}>
              <div className="tree-toggle-thumb" />
            </div>
          </button>

          <div className="tree-field-group">
            <div className="tree-field-label">Short bio</div>
            <textarea
              className="tree-field-input"
              placeholder="1–2 sentences shown in the family book"
              rows={3}
              value={form.notes}
              onChange={(e) => handleField('notes', e.target.value)}
              style={{ resize: 'vertical', lineHeight: 1.5 }}
            />
          </div>
        </div>

        <div className="tree-drawer-footer">
          <button type="button" className="tree-btn-secondary" onClick={onClose}>Cancel</button>
          <button type="button" className="tree-btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </div>
    </>
  );
}

// ── Main component ─────────────────────────────────────────────
export default function KeeperFamilyTree() {
  const { token } = useKeeper();
  const [treeData, setTreeData] = useState(null); // { placed, unplaced, relationships }
  const [allMembers, setAllMembers] = useState([]); // placed + unplaced combined for search
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [selectedId, setSelectedId] = useState(null);
  const [profileMemberId, setProfileMemberId] = useState(null);
  const [memberStories, setMemberStories] = useState([]);
  const [storiesLoading, setStoriesLoading] = useState(false);

  // drawer state: null | { relationship: string|null, anchorId: string|null, preselectedMember: obj|null }
  const [drawerState, setDrawerState] = useState(null);
  const [editMemberId, setEditMemberId] = useState(null);

  // Slot overrides: { [memberId]: { col, row } } — populated from DB on load, updated on drag
  const [slotOverrides, setSlotOverrides] = useState({});
  // Drag state: null | { memberId, ghostX, ghostY, nearestSlot: { col, row } }
  const [dragInfo, setDragInfo] = useState(null);
  const dragStartRef = useRef(null); // { memberId, startMouseX, startMouseY, startNodeX, startNodeY }

  const canvasRef = useRef(null);

  const loadTree = useCallback(async () => {
    try {
      const data = await getTree(token);
      setTreeData(data);
      setAllMembers([...data.placed, ...data.unplaced]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { loadTree(); }, [loadTree]);

  // Sync slot overrides from DB-persisted positions whenever tree data reloads
  useEffect(() => {
    if (!treeData) return;
    const overrides = {};
    for (const m of treeData.placed) {
      if (m.position_col != null && m.position_row != null) {
        overrides[m.id] = { col: m.position_col, row: m.position_row };
      }
    }
    setSlotOverrides(overrides);
  }, [treeData]);

  const placed = treeData?.placed || [];
  const unplaced = treeData?.unplaced || [];
  const relationships = treeData?.relationships || [];

  // Auto-computed slot positions (fall back when no manual override)
  const autoSlots = useMemo(
    () => computeAutoSlots(placed, relationships),
    [placed, relationships]
  );

  // Merged: manual overrides win over auto-layout
  const mergedSlots = useMemo(
    () => ({ ...autoSlots, ...slotOverrides }),
    [autoSlots, slotOverrides]
  );

  // Convert slots → pixel positions for rendering
  const mergedPixelPositions = useMemo(
    () => Object.fromEntries(
      Object.entries(mergedSlots).map(([id, s]) => [id, slotToPixel(s.col, s.row)])
    ),
    [mergedSlots]
  );

  // Pixel positions used for connectors — during drag, show the dragged node at its nearest slot
  const connectorPixelPositions = useMemo(() => {
    if (!dragInfo) return mergedPixelPositions;
    return {
      ...mergedPixelPositions,
      [dragInfo.memberId]: slotToPixel(dragInfo.nearestSlot.col, dragInfo.nearestSlot.row),
    };
  }, [mergedPixelPositions, dragInfo]);

  // Generation levels (for node colour, independent of visual position)
  const generations = useMemo(
    () => computeGenerations(placed, relationships),
    [placed, relationships]
  );

  // Canvas dimensions from merged positions
  const { canvasW, canvasH } = useMemo(() => {
    const positions = Object.values(mergedPixelPositions);
    if (!positions.length) return { canvasW: 600, canvasH: 400 };
    return {
      canvasW: Math.max(...positions.map((p) => p.x)) + NODE_W + CANVAS_PAD,
      canvasH: Math.max(...positions.map((p) => p.y)) + NODE_H + CANVAS_PAD,
    };
  }, [mergedPixelPositions]);

  const connectors = useMemo(
    () => computeConnectors(placed, relationships, connectorPixelPositions),
    [placed, relationships, connectorPixelPositions]
  );

  // Build node descriptors for rendering
  const nodes = useMemo(
    () => placed.map((m) => ({
      member: m,
      ...(mergedPixelPositions[m.id] ?? { x: CANVAS_PAD, y: CANVAS_PAD }),
      gen: generations[m.id] ?? 0,
    })),
    [placed, mergedPixelPositions, generations]
  );

  async function loadMemberStories(memberId) {
    setStoriesLoading(true);
    setMemberStories([]);
    try {
      const res = await getMemberStories(token, memberId);
      setMemberStories(res.stories || []);
    } catch {
      setMemberStories([]);
    } finally {
      setStoriesLoading(false);
    }
  }

  function handleNodeClick(memberId) {
    setSelectedId(memberId);
    if (profileMemberId !== memberId) {
      setProfileMemberId(memberId);
      loadMemberStories(memberId);
    }
  }

  function openAddDrawer(relationship, anchorId) {
    setDrawerState({ relationship, anchorId, preselectedMember: null });
  }

  function openLinkDrawer(unplacedMember) {
    setDrawerState({ relationship: null, anchorId: null, preselectedMember: unplacedMember });
  }

  async function handleSaved() {
    setDrawerState(null);
    setSelectedId(null);
    await loadTree();
  }

  async function handleEditSaved() {
    setEditMemberId(null);
    await loadTree();
  }

  async function handleDeleteMember(memberId) {
    await deleteTreeMember(token, memberId);
    setProfileMemberId(null);
    setSelectedId(null);
    await loadTree();
  }

  async function handleLink(linkMember, relationship) {
    const { anchorId } = drawerState;
    if (!anchorId || !relationship) return;
    await createRelationship(token, {
      member_id: anchorId,
      related_member_id: linkMember.id,
      relationship_type: relationship,
    });
    setDrawerState(null);
    setSelectedId(null);
    await loadTree();
  }

  // ── Drag handlers ──────────────────────────────────────────────
  function handleNodeMouseDown(e, memberId) {
    e.preventDefault();
    const pos = mergedPixelPositions[memberId];
    if (!pos) return;
    dragStartRef.current = {
      memberId,
      startMouseX: e.clientX,
      startMouseY: e.clientY,
      startNodeX: pos.x,
      startNodeY: pos.y,
    };
  }

  function handleCanvasMouseMove(e) {
    if (!dragStartRef.current) return;
    const { memberId, startMouseX, startMouseY, startNodeX, startNodeY } = dragStartRef.current;
    const dx = e.clientX - startMouseX;
    const dy = e.clientY - startMouseY;
    if (Math.abs(dx) < 4 && Math.abs(dy) < 4) return; // dead zone
    const ghostX = startNodeX + dx;
    const ghostY = startNodeY + dy;
    setDragInfo({ memberId, ghostX, ghostY, nearestSlot: snapToSlot(ghostX, ghostY) });
  }

  function commitDrag(memberId, nearestSlot) {
    const vacatedSlot = mergedSlots[memberId];
    // Check if another node occupies the target slot
    const occupantEntry = Object.entries(mergedSlots).find(
      ([id, s]) => id !== memberId && s.col === nearestSlot.col && s.row === nearestSlot.row
    );
    setSlotOverrides((prev) => {
      const next = { ...prev, [memberId]: nearestSlot };
      if (occupantEntry) next[occupantEntry[0]] = vacatedSlot;
      return next;
    });
    updateTreeMember(token, memberId, { position_col: nearestSlot.col, position_row: nearestSlot.row }).catch(() => {});
    if (occupantEntry) {
      updateTreeMember(token, occupantEntry[0], { position_col: vacatedSlot.col, position_row: vacatedSlot.row }).catch(() => {});
    }
  }

  function handleCanvasMouseUp(e) {
    if (!dragStartRef.current) {
      // Clicked canvas background (not a node)
      setSelectedId(null);
      return;
    }
    const { memberId } = dragStartRef.current;
    dragStartRef.current = null;

    if (!dragInfo) {
      // No significant movement → treat as node click
      handleNodeClick(memberId);
      return;
    }

    const { nearestSlot } = dragInfo;
    setDragInfo(null);
    commitDrag(memberId, nearestSlot);
  }

  async function handleResetLayout() {
    const overriddenIds = Object.keys(slotOverrides);
    if (!overriddenIds.length) return;
    setSlotOverrides({});
    await Promise.all(
      overriddenIds.map((id) =>
        updateTreeMember(token, id, { position_col: null, position_row: null }).catch(() => {})
      )
    );
  }

  // ── Derived render values ──────────────────────────────────────
  const selectedNodePos = selectedId ? mergedPixelPositions[selectedId] : null;
  const selectedNode = selectedNodePos ? { x: selectedNodePos.x, y: selectedNodePos.y } : null;

  const profileMember = treeData
    ? [...placed, ...unplaced].find((m) => m.id === profileMemberId)
    : null;

  const drawerAnchor = drawerState?.anchorId && treeData
    ? placed.find((m) => m.id === drawerState.anchorId)
    : null;

  const editMember = editMemberId && treeData
    ? [...placed, ...unplaced].find((m) => m.id === editMemberId)
    : null;

  const hasOverrides = Object.keys(slotOverrides).length > 0;
  const isEmpty = placed.length === 0;
  const isDraggingActive = dragInfo !== null;

  if (loading) {
    return (
      <div className="keeper-loading">
        <div className="keeper-spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="keeper-loading" style={{ flexDirection: 'column', gap: 8 }}>
        <div style={{ color: 'var(--danger)', fontWeight: 600 }}>Failed to load tree</div>
        <div style={{ color: 'var(--faint)', fontSize: 12 }}>{error}</div>
        <button className="tree-btn-primary" style={{ marginTop: 8, maxWidth: 160 }} onClick={loadTree}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="tree-page">
      <div className="tree-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div className="tree-header-eyebrow">Roeung · ❧ Keeper · Family tree</div>
            <div className="tree-header-title">Building the family tree</div>
            <div className="tree-header-sub">
              Drag nodes to rearrange. Relationships stay intact.
            </div>
          </div>
          {hasOverrides && (
            <button type="button" className="tree-reset-layout-btn" onClick={handleResetLayout}>
              Reset layout
            </button>
          )}
        </div>
      </div>

      <div className="tree-body">
        {/* Left: unplaced sidebar */}
        <UnplacedSidebar
          unplaced={unplaced}
          onChipClick={openLinkDrawer}
        />

        {/* Centre: canvas */}
        {isEmpty ? (
          <div className="tree-canvas-wrap" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div className="tree-empty">
              <div className="tree-empty-icon">🌳</div>
              <div className="tree-empty-title">Start your family tree</div>
              <div className="tree-empty-sub">
                Add the first family member to begin. Everyone else grows from there.
              </div>
              <button
                type="button"
                className="tree-empty-btn"
                onClick={() => setDrawerState({ relationship: null, anchorId: null, preselectedMember: null })}
              >
                Add first member
              </button>
            </div>
          </div>
        ) : (
          <div
            className={`tree-canvas-wrap${isDraggingActive ? ' dragging-active' : ''}`}
            onMouseMove={handleCanvasMouseMove}
            onMouseUp={handleCanvasMouseUp}
          >
            <div
              className="tree-canvas"
              ref={canvasRef}
              style={{ width: canvasW, height: canvasH }}
            >
              {/* Info chip */}
              <div className="tree-canvas-info" style={{ position: 'absolute' }}>
                <span className="tree-canvas-info-count">❧ {placed.length} members</span>
                <span className="tree-canvas-info-dot" />
                <span className="tree-canvas-info-unplaced">{unplaced.length} unplaced</span>
              </div>

              {/* SVG connectors (behind nodes) */}
              <ConnectorSVG connectors={connectors} canvasW={canvasW} canvasH={canvasH} />

              {/* Drop-zone indicator at nearest slot during drag */}
              {dragInfo && (() => {
                const dz = slotToPixel(dragInfo.nearestSlot.col, dragInfo.nearestSlot.row);
                return (
                  <div
                    className="tree-drop-zone"
                    style={{ left: dz.x, top: dz.y, width: NODE_W, height: NODE_H }}
                  />
                );
              })()}

              {/* Nodes */}
              {nodes.map((node) => {
                const isDragging = dragInfo?.memberId === node.member.id;
                const renderX = isDragging ? dragInfo.ghostX : node.x;
                const renderY = isDragging ? dragInfo.ghostY : node.y;
                return (
                  <TreeNode
                    key={node.member.id}
                    node={{ ...node, x: renderX, y: renderY }}
                    isSelected={node.member.id === selectedId}
                    isDragging={isDragging}
                    onMouseDown={handleNodeMouseDown}
                  />
                );
              })}

              {/* Action ring around selected node (hidden during drag) */}
              {selectedNode && !isDraggingActive && (
                <NodeActionRing
                  node={selectedNode}
                  onAdd={(rel) => openAddDrawer(rel, selectedId)}
                />
              )}
            </div>
          </div>
        )}

        {/* Right: profile panel */}
        {profileMember && (
          <ProfilePanel
            member={profileMember}
            stories={memberStories}
            loading={storiesLoading}
            onClose={() => { setProfileMemberId(null); setSelectedId(null); }}
            onAddRelationship={(rel) => openAddDrawer(rel, profileMemberId)}
            onEdit={() => setEditMemberId(profileMemberId)}
            onDelete={() => handleDeleteMember(profileMemberId)}
          />
        )}
      </div>

      {/* Add / Link drawer */}
      {drawerState && (
        <AddMemberDrawer
          anchor={drawerAnchor}
          relationship={drawerState.relationship}
          allMembers={allMembers}
          placed={placed}
          onClose={() => setDrawerState(null)}
          onSaved={handleSaved}
          onLink={handleLink}
        />
      )}

      {/* Edit member drawer */}
      {editMember && (
        <EditMemberDrawer
          member={editMember}
          onClose={() => setEditMemberId(null)}
          onSaved={handleEditSaved}
        />
      )}
    </div>
  );
}
