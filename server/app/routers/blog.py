"""Blog — CRUD for posts/categories, public listing."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..database import get_db
from ..models import AdminUser, BlogCategory, BlogPost
from ..schemas import BlogCategoryIn, BlogPostIn
from ..utils import slugify

router = APIRouter(tags=["blog"])


# ───────────────────────────── Public ─────────────────────────────

@router.get("/api/blog/posts")
def list_posts(
    db: Session = Depends(get_db),
    category: str | None = Query(None),
    tag: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=50),
):
    q = db.query(BlogPost).filter(BlogPost.published == True).order_by(BlogPost.created_at.desc())
    if category:
        q = q.filter(BlogPost.category_id == category)
    total = q.count()
    posts = q.offset((page - 1) * limit).limit(limit).all()
    if tag:
        posts = [p for p in posts if tag in (p.tags or [])]
    return {
        "posts": [
            {
                "id": p.id, "slug": p.slug, "title": p.title, "excerpt": p.excerpt,
                "cover_image": p.cover_image, "author": p.author,
                "category_id": p.category_id, "tags": p.tags,
                "created_at": p.created_at.isoformat(), "views": p.views,
            }
            for p in posts
        ],
        "total": total,
        "page": page,
    }


@router.get("/api/blog/posts/{slug_or_id}")
def get_post(slug_or_id: str, db: Session = Depends(get_db)):
    post = db.query(BlogPost).filter(
        (BlogPost.slug == slug_or_id) | (BlogPost.id == int(slug_or_id) if slug_or_id.isdigit() else False)
    ).first()
    if not post or not post.published:
        raise HTTPException(status_code=404, detail="Post not found")
    post.views = (post.views or 0) + 1
    db.commit()
    return {
        "id": post.id, "slug": post.slug, "title": post.title,
        "excerpt": post.excerpt, "body": post.body,
        "cover_image": post.cover_image, "author": post.author,
        "category_id": post.category_id, "tags": post.tags,
        "related_products": post.related_products,
        "seo_title": post.seo_title, "seo_description": post.seo_description,
        "created_at": post.created_at.isoformat(), "views": post.views,
    }


@router.get("/api/blog/categories")
def list_blog_categories(db: Session = Depends(get_db)):
    return [
        {"id": c.id, "name": c.name, "sort_order": c.sort_order}
        for c in db.query(BlogCategory).order_by(BlogCategory.sort_order).all()
    ]


# ───────────────────────────── Admin ─────────────────────────────

@router.get("/api/admin/blog/posts")
def admin_list_posts(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
    return [
        {
            "id": p.id, "slug": p.slug, "title": p.title, "excerpt": p.excerpt,
            "cover_image": p.cover_image, "author": p.author,
            "category_id": p.category_id, "tags": p.tags, "published": p.published,
            "views": p.views, "created_at": p.created_at.isoformat(),
        }
        for p in posts
    ]


@router.post("/api/admin/blog/posts")
def create_post(data: BlogPostIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    slug = data.slug or slugify(data.title)
    if db.query(BlogPost).filter(BlogPost.slug == slug).first():
        slug = f"{slug}-{db.query(BlogPost).count() + 1}"
    post = BlogPost(
        slug=slug, title=data.title, excerpt=data.excerpt, body=data.body,
        cover_image=data.cover_image, author=data.author,
        category_id=data.category_id or None, tags=data.tags,
        related_products=data.related_products, published=data.published,
        seo_title=data.seo_title, seo_description=data.seo_description,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"ok": True, "id": post.id, "slug": post.slug}


@router.put("/api/admin/blog/posts/{post_id}")
def update_post(post_id: int, data: BlogPostIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if data.slug and data.slug != post.slug:
        if db.query(BlogPost).filter(BlogPost.slug == data.slug, BlogPost.id != post_id).first():
            raise HTTPException(status_code=400, detail="Slug already exists")
        post.slug = data.slug
    post.title = data.title
    post.excerpt = data.excerpt
    post.body = data.body
    post.cover_image = data.cover_image
    post.author = data.author
    post.category_id = data.category_id or None
    post.tags = data.tags
    post.related_products = data.related_products
    post.published = data.published
    post.seo_title = data.seo_title
    post.seo_description = data.seo_description
    db.commit()
    return {"ok": True}


@router.delete("/api/admin/blog/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if post:
        db.delete(post)
        db.commit()
    return {"ok": True}


@router.post("/api/admin/blog/categories")
def upsert_blog_category(data: BlogCategoryIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    cid = data.id or slugify(data.name)
    c = db.query(BlogCategory).filter(BlogCategory.id == cid).first()
    if not c:
        c = BlogCategory(id=cid)
        db.add(c)
    c.name = data.name
    c.sort_order = data.sort_order
    db.commit()
    return {"ok": True, "id": c.id}


@router.delete("/api/admin/blog/categories/{cid}")
def delete_blog_category(cid: str, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    c = db.query(BlogCategory).filter(BlogCategory.id == cid).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}
