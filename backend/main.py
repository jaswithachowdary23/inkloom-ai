from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uvicorn

from database import (
    init_db, get_db, BrandWorkspace, Guideline, Draft, Finding, Revision
)
from checker import run_full_check, generate_suggestion_rewrite

app = FastAPI(
    title="Inkloom AI",
    description="Intelligent Brand Governance Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Pydantic schemas ----------
class GuidelineCreate(BaseModel):
    category: str
    title: str
    content: str
    severity: str = "medium"
    is_exact_match: bool = False


class GuidelineOut(GuidelineCreate):
    id: int
    class Config:
        from_attributes = True


class WorkspaceCreate(BaseModel):
    name: str
    description: str = ""


class WorkspaceOut(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    guidelines: List[GuidelineOut] = []
    class Config:
        from_attributes = True


class DraftCreate(BaseModel):
    workspace_id: int
    title: str = "Untitled Draft"
    content: str
    channel: str = "social"


class FindingOut(BaseModel):
    id: int
    category: str
    severity: str
    title: str
    explanation: str
    original_text: Optional[str]
    suggested_text: Optional[str]
    is_rule_based: bool
    confidence: float
    status: str
    class Config:
        from_attributes = True


class DraftOut(BaseModel):
    id: int
    workspace_id: int
    title: str
    content: str
    channel: str
    status: str
    created_at: datetime
    updated_at: datetime
    findings: List[FindingOut] = []
    class Config:
        from_attributes = True


class FindingUpdate(BaseModel):
    status: str  # accepted, rejected, modified
    suggested_text: Optional[str] = None


class ApprovalAction(BaseModel):
    action: str  # approve, request_changes
    comment: str = ""


class RevisionOut(BaseModel):
    id: int
    content: str
    comment: str
    action: str
    created_at: datetime
    class Config:
        from_attributes = True


# ---------- Startup ----------
@app.on_event("startup")
def on_startup():
    init_db()
    # Seed a default workspace if empty
    db = next(get_db())
    if db.query(BrandWorkspace).count() == 0:
        ws = BrandWorkspace(
            name="Demo Brand – Inkloom Co",
            description="Sample workspace with starter brand guidelines for the hackathon demo."
        )
        db.add(ws)
        db.commit()
        db.refresh(ws)
        
        sample_guidelines = [
            Guideline(workspace_id=ws.id, category="terminology", title="Preferred term for AI",
                      content="Always expand 'AI' to 'artificial intelligence' on first use in a piece.",
                      severity="low", is_exact_match=False),
            Guideline(workspace_id=ws.id, category="prohibited", title="No absolute guarantees",
                      content="guaranteed", severity="high", is_exact_match=True),
            Guideline(workspace_id=ws.id, category="claim", title="Superlative claims need evidence",
                      content="best in the world", severity="high", is_exact_match=True),
            Guideline(workspace_id=ws.id, category="tone", title="Professional voice",
                      content="Maintain a confident, clear and professional tone. Avoid slang and excessive hype.",
                      severity="medium", is_exact_match=False),
            Guideline(workspace_id=ws.id, category="preferred", title="Customer language",
                      content="Prefer 'clients' over 'customers' in formal materials.",
                      severity="low", is_exact_match=False),
            Guideline(workspace_id=ws.id, category="prohibited", title="Safety claims",
                      content="100% safe", severity="critical", is_exact_match=True),
        ]
        db.add_all(sample_guidelines)
        db.commit()
    db.close()


# ---------- Workspaces ----------
@app.get("/api/workspaces", response_model=List[WorkspaceOut])
def list_workspaces(db: Session = Depends(get_db)):
    return db.query(BrandWorkspace).all()


@app.post("/api/workspaces", response_model=WorkspaceOut, status_code=201)
def create_workspace(data: WorkspaceCreate, db: Session = Depends(get_db)):
    ws = BrandWorkspace(name=data.name, description=data.description)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


@app.get("/api/workspaces/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(workspace_id: int, db: Session = Depends(get_db)):
    ws = db.query(BrandWorkspace).filter(BrandWorkspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return ws


@app.post("/api/workspaces/{workspace_id}/guidelines", response_model=GuidelineOut, status_code=201)
def add_guideline(workspace_id: int, data: GuidelineCreate, db: Session = Depends(get_db)):
    ws = db.query(BrandWorkspace).filter(BrandWorkspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    g = Guideline(workspace_id=workspace_id, **data.model_dump())
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@app.get("/api/workspaces/{workspace_id}/guidelines", response_model=List[GuidelineOut])
def list_guidelines(workspace_id: int, db: Session = Depends(get_db)):
    return db.query(Guideline).filter(Guideline.workspace_id == workspace_id).all()


# ---------- Drafts & Checking ----------
@app.post("/api/drafts", response_model=DraftOut, status_code=201)
def create_draft(data: DraftCreate, db: Session = Depends(get_db)):
    ws = db.query(BrandWorkspace).filter(BrandWorkspace.id == data.workspace_id).first()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    
    draft = Draft(
        workspace_id=data.workspace_id,
        title=data.title,
        content=data.content,
        channel=data.channel,
        status="draft"
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    
    # Record revision
    rev = Revision(draft_id=draft.id, content=data.content, action="created", comment="Initial draft")
    db.add(rev)
    db.commit()
    
    # Run checks immediately
    guidelines = [
        {
            "id": g.id,
            "category": g.category,
            "title": g.title,
            "content": g.content,
            "severity": g.severity,
            "is_exact_match": g.is_exact_match
        }
        for g in ws.guidelines
    ]
    
    results = run_full_check(data.content, guidelines, data.channel)
    
    for r in results:
        finding = Finding(
            draft_id=draft.id,
            category=r.category,
            severity=r.severity,
            title=r.title,
            explanation=r.explanation,
            original_text=r.original_text or "",
            suggested_text=r.suggested_text,
            guideline_id=r.guideline_id,
            is_rule_based=r.is_rule_based,
            confidence=r.confidence,
            status="open"
        )
        db.add(finding)
    db.commit()
    db.refresh(draft)
    return draft


@app.get("/api/drafts/{draft_id}", response_model=DraftOut)
def get_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(404, "Draft not found")
    return draft


@app.get("/api/workspaces/{workspace_id}/drafts", response_model=List[DraftOut])
def list_drafts(workspace_id: int, db: Session = Depends(get_db)):
    return db.query(Draft).filter(Draft.workspace_id == workspace_id).order_by(Draft.updated_at.desc()).all()


@app.post("/api/drafts/{draft_id}/recheck", response_model=DraftOut)
def recheck_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(404, "Draft not found")
    
    # Clear old open findings
    db.query(Finding).filter(Finding.draft_id == draft_id).delete()
    
    guidelines = [
        {
            "id": g.id,
            "category": g.category,
            "title": g.title,
            "content": g.content,
            "severity": g.severity,
            "is_exact_match": g.is_exact_match
        }
        for g in draft.workspace.guidelines
    ]
    
    results = run_full_check(draft.content, guidelines, draft.channel)
    for r in results:
        finding = Finding(
            draft_id=draft.id,
            category=r.category,
            severity=r.severity,
            title=r.title,
            explanation=r.explanation,
            original_text=r.original_text or "",
            suggested_text=r.suggested_text,
            guideline_id=r.guideline_id,
            is_rule_based=r.is_rule_based,
            confidence=r.confidence,
            status="open"
        )
        db.add(finding)
    db.commit()
    db.refresh(draft)
    return draft


@app.patch("/api/findings/{finding_id}", response_model=FindingOut)
def update_finding(finding_id: int, data: FindingUpdate, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(404, "Finding not found")
    finding.status = data.status
    if data.suggested_text is not None:
        finding.suggested_text = data.suggested_text
    db.commit()
    db.refresh(finding)
    return finding


@app.post("/api/drafts/{draft_id}/apply-suggestions")
def apply_suggestions(draft_id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(404, "Draft not found")
    
    open_findings = [f for f in draft.findings if f.status == "open" and f.suggested_text]
    new_content = draft.content
    for f in open_findings:
        if f.original_text and f.original_text in new_content:
            new_content = new_content.replace(f.original_text, f.suggested_text, 1)
            f.status = "accepted"
    
    draft.content = new_content
    draft.updated_at = datetime.utcnow()
    
    rev = Revision(
        draft_id=draft.id,
        content=new_content,
        action="edited",
        comment="Applied accepted suggestions"
    )
    db.add(rev)
    db.commit()
    return {"content": new_content, "applied": len(open_findings)}


@app.post("/api/drafts/{draft_id}/submit", response_model=DraftOut)
def submit_for_review(draft_id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(404, "Draft not found")
    draft.status = "under_review"
    draft.updated_at = datetime.utcnow()
    rev = Revision(draft_id=draft.id, content=draft.content, action="submitted", comment="Submitted for human approval")
    db.add(rev)
    db.commit()
    db.refresh(draft)
    return draft


@app.post("/api/drafts/{draft_id}/approve", response_model=DraftOut)
def approve_or_request(draft_id: int, data: ApprovalAction, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(404, "Draft not found")
    
    if data.action == "approve":
        draft.status = "approved"
        action = "approved"
    else:
        draft.status = "changes_requested"
        action = "changes_requested"
    
    draft.updated_at = datetime.utcnow()
    rev = Revision(
        draft_id=draft.id,
        content=draft.content,
        action=action,
        comment=data.comment or ("Approved by reviewer" if data.action == "approve" else "Changes requested")
    )
    db.add(rev)
    db.commit()
    db.refresh(draft)
    return draft


@app.get("/api/drafts/{draft_id}/revisions", response_model=List[RevisionOut])
def get_revisions(draft_id: int, db: Session = Depends(get_db)):
    return db.query(Revision).filter(Revision.draft_id == draft_id).order_by(Revision.created_at.desc()).all()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Inkloom AI", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)