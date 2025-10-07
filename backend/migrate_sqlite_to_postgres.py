"""
One-shot migration script: copy data from a local SQLite DB to a Postgres (or other) DATABASE_URL.

Usage:
  # set TARGET_DATABASE_URL (example Postgres)
  $env:TARGET_DATABASE_URL = 'postgres://user:pass@host:5432/dbname'
  python migrate_sqlite_to_postgres.py --source sqlite:///./financebot.db --target $env:TARGET_DATABASE_URL

Options:
  --yes    Skip confirmation prompt (use with caution)

This script will:
  - Create tables on the target if they do not exist
  - Copy users, documents, conversation threads, messages, thread-document associations
  - Preserve external UUID fields like Document.document_id and ConversationThread.thread_id

WARNING: Always back up your target DB before running.
"""

import argparse
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import (
    Base, User, Document, Conversation, ConversationThread,
    ConversationMessage, ThreadDocument
)
from datetime import datetime


def connect(url):
    if url.startswith('sqlite'):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url)


def main():
    parser = argparse.ArgumentParser(description='Migrate SQLite DB to Postgres (or other target)')
    parser.add_argument('--source', default='sqlite:///./financebot.db', help='Source SQLAlchemy URL')
    parser.add_argument('--target', required=True, help='Target SQLAlchemy URL (e.g. postgres://...)')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation')
    args = parser.parse_args()

    source_url = args.source
    target_url = args.target

    print(f"Source: {source_url}")
    print(f"Target: {target_url}")

    if not args.yes:
        resp = input('This will copy data from source -> target. Continue? Type YES to proceed: ')
        if resp.strip() != 'YES':
            print('Aborting')
            return

    # Connect
    src_engine = connect(source_url)
    dst_engine = connect(target_url)

    SrcSession = sessionmaker(bind=src_engine)
    DstSession = sessionmaker(bind=dst_engine)

    # Ensure target has tables
    print('Creating tables on target (if not present)')
    Base.metadata.create_all(bind=dst_engine)

    src_s = SrcSession()
    dst_s = DstSession()

    try:
        # Map old PK -> new PK
        users_map = {}
        docs_map = {}
        threads_map = {}

        print('Copying users...')
        src_users = src_s.query(User).all()
        for u in src_users:
            new_u = User(session_id=u.session_id, created_at=u.created_at)
            dst_s.add(new_u)
            dst_s.flush()
            users_map[u.id] = new_u.id
        dst_s.commit()
        print(f'  copied {len(users_map)} users')

        print('Copying documents...')
        src_docs = src_s.query(Document).all()
        for d in src_docs:
            new_user_id = users_map.get(d.user_id)
            new_d = Document(
                document_id=d.document_id,
                filename=d.filename,
                document_type=d.document_type,
                content_hash=d.content_hash,
                content=d.content,
                summary=d.summary,
                risk_score=d.risk_score,
                upload_date=d.upload_date,
                user_id=new_user_id
            )
            dst_s.add(new_d)
            dst_s.flush()
            docs_map[d.id] = new_d.id
        dst_s.commit()
        print(f'  copied {len(docs_map)} documents')

        print('Copying conversation threads...')
        src_threads = src_s.query(ConversationThread).all()
        for t in src_threads:
            new_user_id = users_map.get(t.user_id)
            new_t = ConversationThread(
                thread_id=t.thread_id,
                title=t.title,
                created_at=t.created_at,
                updated_at=t.updated_at,
                user_id=new_user_id
            )
            dst_s.add(new_t)
            dst_s.flush()
            threads_map[t.id] = new_t.id
        dst_s.commit()
        print(f'  copied {len(threads_map)} threads')

        print('Copying thread-document associations...')
        src_td = src_s.query(ThreadDocument).all()
        td_count = 0
        for td in src_td:
            new_thread_id = threads_map.get(td.thread_id)
            new_doc_id = docs_map.get(td.document_id)
            if new_thread_id and new_doc_id:
                new_td = ThreadDocument(thread_id=new_thread_id, document_id=new_doc_id, uploaded_at=td.uploaded_at)
                dst_s.add(new_td)
                td_count += 1
        dst_s.commit()
        print(f'  copied {td_count} thread-document links')

        print('Copying conversation messages...')
        src_msgs = src_s.query(ConversationMessage).all()
        msg_count = 0
        for m in src_msgs:
            new_thread_pk = threads_map.get(m.thread_id)
            # document_id in message refers to Document.id
            new_doc_pk = docs_map.get(m.document_id) if m.document_id else None
            if not new_thread_pk:
                # skip messages pointing at missing thread (shouldn't happen)
                continue
            new_m = ConversationMessage(
                thread_id=new_thread_pk,
                role=m.role,
                content=m.content,
                timestamp=m.timestamp,
                document_id=new_doc_pk
            )
            dst_s.add(new_m)
            msg_count += 1
        dst_s.commit()
        print(f'  copied {msg_count} messages')

        print('Copying conversations (question/answer) linked to documents...')
        src_convs = src_s.query(Conversation).all()
        conv_count = 0
        for c in src_convs:
            new_user_id = users_map.get(c.user_id)
            new_doc_pk = docs_map.get(c.document_id) if c.document_id else None
            if not new_user_id:
                continue
            new_c = Conversation(
                question=c.question,
                answer=c.answer,
                timestamp=c.timestamp,
                user_id=new_user_id,
                document_id=new_doc_pk
            )
            dst_s.add(new_c)
            conv_count += 1
        dst_s.commit()
        print(f'  copied {conv_count} conversations')

        print('Migration complete!')

    except Exception as e:
        dst_s.rollback()
        print('Error during migration:', str(e))
    finally:
        src_s.close()
        dst_s.close()


if __name__ == '__main__':
    main()
