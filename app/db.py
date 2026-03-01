"""
SQLite3 database operations for medication reconciliation.
"""
import os
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    createMedSnap,
    createMedConf,
    createPatMedRec,
)


class Database:
    """SQLite3 database operations."""

    def __init__(self, db_path=None):
        """
        Initialize SQLite database connection.
        
        Args:
            db_path: Path to SQLite database file.
                    Defaults to medication_reconciliation.db
        """
        if db_path is None:
            db_path = os.getenv(
                "SQLITE_DB_PATH", "medication_reconciliation.db"
            )
        
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._setup_tables()
    
    def _setup_tables(self):
        """Set up tables and indexes."""
        cur = self.conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                clinic_id TEXT NOT NULL,
                snapshots_json TEXT NOT NULL,
                conflicts_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_clinic_id 
            ON patients(clinic_id)
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_clinic_updated 
            ON patients(clinic_id, updated_at)
        """)
        
        self.conn.commit()
    
    def upsertPatRec(self, rec):
        """
        Upsert patient medication record (dict).
        
        Args:
            rec: Patient record dict to save.
        
        Returns:
            The patId.
        """
        rec['updatAt'] = datetime.now(timezone.utc)
        
        cur = self.conn.cursor()
        
        snapsToSave = []
        for s in rec['snaps']:
            snapCopy = dict(s)
            if isinstance(snapCopy.get('capturAt'), datetime):
                snapCopy['capturAt'] = snapCopy['capturAt'].isoformat()
            snapsToSave.append(snapCopy)
        
        confsToSave = []
        for c in rec['confs']:
            confCopy = dict(c)
            if isinstance(confCopy.get('detectAt'), datetime):
                confCopy['detectAt'] = confCopy['detectAt'].isoformat()
            if isinstance(confCopy.get('resolveAt'), datetime):
                confCopy['resolveAt'] = confCopy['resolveAt'].isoformat()
            confsToSave.append(confCopy)
        
        creatAtStr = rec['creatAt'].isoformat() if isinstance(rec['creatAt'], datetime) else rec['creatAt']
        updatAtStr = rec['updatAt'].isoformat() if isinstance(rec['updatAt'], datetime) else rec['updatAt']
        
        cur.execute("""
            INSERT OR REPLACE INTO patients
            (patient_id, clinic_id, snapshots_json, conflicts_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            rec['patId'],
            rec['clinId'],
            json.dumps(snapsToSave),
            json.dumps(confsToSave),
            creatAtStr,
            updatAtStr,
        ))
        
        self.conn.commit()
        return rec['patId']
    
    def getPatRec(self, patId):
        """Retrieve patient medication record (returns dict)."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM patients WHERE patient_id = ?",
            (patId,)
        )
        row = cur.fetchone()
        
        if row:
            snapsData = json.loads(row['snapshots_json'])
            confsData = json.loads(row['conflicts_json'])
            
            for s in snapsData:
                if isinstance(s.get('capturAt'), str):
                    s['capturAt'] = datetime.fromisoformat(s['capturAt'])
            
            for c in confsData:
                if isinstance(c.get('detectAt'), str):
                    c['detectAt'] = datetime.fromisoformat(c['detectAt'])
                if c.get('resolveAt') and isinstance(c['resolveAt'], str):
                    c['resolveAt'] = datetime.fromisoformat(c['resolveAt'])
            
            creatAt = datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at']
            updatAt = datetime.fromisoformat(row['updated_at']) if isinstance(row['updated_at'], str) else row['updated_at']
            
            return createPatMedRec(
                patId=row['patient_id'],
                clinId=row['clinic_id'],
                snaps=snapsData,
                confs=confsData,
                creatAt=creatAt,
                updatAt=updatAt,
            )
        return None
    
    def addSnap(self, patId, snap):
        """Add medication snapshot to patient record."""
        pat = self.getPatRec(patId)
        if pat:
            pat['snaps'].append(snap)
            pat['updatAt'] = datetime.now(timezone.utc)
            self.upsertPatRec(pat)
    
    def addConf(self, patId, confs):
        """Add detected conflicts to patient record."""
        if not confs:
            return
        
        pat = self.getPatRec(patId)
        if pat:
            pat['confs'].extend(confs)
            pat['updatAt'] = datetime.now(timezone.utc)
            self.upsertPatRec(pat)
    
    def resolveConf(self, patId, confIdx, resoReason, resolveBy):
        """Mark conflict as resolved."""
        pat = self.getPatRec(patId)
        if pat and 0 <= confIdx < len(pat['confs']):
            conf = pat['confs'][confIdx]
            conf['resoStatus'] = "resolved"
            conf['resoReason'] = resoReason
            conf['resolveBy'] = resolveBy
            conf['resolveAt'] = datetime.now(timezone.utc)
            pat['updatAt'] = datetime.now(timezone.utc)
            self.upsertPatRec(pat)
    
    def findPatUnresol(self, clinId=None, minConfs=1):
        """
        Find patients with unresolved conflicts.
        
        Args:
            clinId: Filter by clinic (optional).
            minConfs: Minimum number of unresolved conflicts.
        
        Returns:
            List of patient record dicts.
        """
        cur = self.conn.cursor()
        
        if clinId:
            cur.execute("SELECT * FROM patients WHERE clinic_id = ?", (clinId,))
        else:
            cur.execute("SELECT * FROM patients")
        
        rows = cur.fetchall()
        results = []
        
        for row in rows:
            snapsData = json.loads(row['snapshots_json'])
            confsData = json.loads(row['conflicts_json'])
            
            for s in snapsData:
                if isinstance(s.get('capturAt'), str):
                    s['capturAt'] = datetime.fromisoformat(s['capturAt'])
            
            for c in confsData:
                if isinstance(c.get('detectAt'), str):
                    c['detectAt'] = datetime.fromisoformat(c['detectAt'])
                if c.get('resolveAt') and isinstance(c['resolveAt'], str):
                    c['resolveAt'] = datetime.fromisoformat(c['resolveAt'])
            
            unresolved = [c for c in confsData if c.get('resoStatus') == "unresolved"]
            
            if len(unresolved) >= minConfs:
                creatAt = datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at']
                updatAt = datetime.fromisoformat(row['updated_at']) if isinstance(row['updated_at'], str) else row['updated_at']
                
                rec = createPatMedRec(
                    patId=row['patient_id'],
                    clinId=row['clinic_id'],
                    snaps=snapsData,
                    confs=unresolved,
                    creatAt=creatAt,
                    updatAt=updatAt,
                )
                results.append(rec)
        
        return results
    
    def getConfSummary(self, clinId=None, startDate=None, endDate=None):
        """
        Get aggregated conflict statistics.
        
        Args:
            clinId: Optional clinic filter.
            startDate: Optional start date for detectAt.
            endDate: Optional end date for detectAt.
        
        Returns:
            Dictionary with summary statistics.
        """
        cur = self.conn.cursor()
        
        if clinId:
            cur.execute("SELECT * FROM patients WHERE clinic_id = ?", (clinId,))
        else:
            cur.execute("SELECT * FROM patients")
        
        rows = cur.fetchall()
        
        totalPats = len(rows)
        confStats = {}
        
        for row in rows:
            confsData = json.loads(row['conflicts_json'])
            
            for c in confsData:
                if isinstance(c.get('detectAt'), str):
                    c['detectAt'] = datetime.fromisoformat(c['detectAt'])
                if c.get('resolveAt') and isinstance(c['resolveAt'], str):
                    c['resolveAt'] = datetime.fromisoformat(c['resolveAt'])
            
            for conf in confsData:
                confType = conf.get('confType')
                
                if confType not in confStats:
                    confStats[confType] = {"count": 0, "unresolved": 0}
                
                confStats[confType]["count"] += 1
                if conf.get('resoStatus') == "unresolved":
                    confStats[confType]["unresolved"] += 1
        
        return {
            "totalPats": totalPats,
            "confStats": [
                {"_id": k, **v} for k, v in confStats.items()
            ]
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()
