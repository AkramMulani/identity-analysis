import os
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_from_directory
from backend import db, embedder, compare as cmp
from pathlib import Path
from backend.embedder import extract_embeddings
from backend.compare import cosine_similarity
from backend.identity_analysis_utility import IdentityAnalysisUtility
import sqlite3
import tempfile
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = os.environ.get('FACIAL_SECRET_KEY', 'dev-secret-key-change-me')

identityUtility = IdentityAnalysisUtility()
DB_PATH = os.environ.get('FACIAL_DB', 'data/facial.db')
API_KEY = os.environ.get('FACIAL_API_KEY', '')
Path('photos').mkdir(parents=True, exist_ok=True)
Path('data').mkdir(parents=True, exist_ok=True)


def ensure_db():
    db.init_db(DB_PATH)


def current_admin():
    admin_id = session.get('admin_id')
    if not admin_id:
        return None
    username = session.get('admin_username')
    if not username:
        return None
    return {
        'id': admin_id,
        'username': username,
        'display_name': session.get('admin_display_name')
    }


def get_primary_face_photo_url(person_id):
    photo = db.get_primary_photo_by_person_id(DB_PATH, person_id)
    if not photo or not photo.get('path'):
        return None
    return url_for('person_photo', filename=Path(photo['path']).name)


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_admin():
            return redirect(url_for('admin_login'))
        return view_func(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_admin_context():
    return {'current_admin': current_admin()}


@app.route('/photos/<path:filename>')
def person_photo(filename):
    return send_from_directory('photos', filename)

# Home page with navigation
@app.route('/')
def home():
    if current_admin():
        return redirect(url_for('dashboard'))
    return redirect(url_for('admin_login'))


@app.route('/dashboard')
@admin_required
def dashboard():
    ensure_db()
    stats = db.get_person_counts(DB_PATH)
    admin_total = db.get_admin_count(DB_PATH)
    persons = db.get_all_persons(DB_PATH)
    recent_persons = persons[-5:][::-1] if persons else []
    return render_template(
        'dashboard.html',
        stats=stats,
        admin_total=admin_total,
        recent_persons=recent_persons,
    )


@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    ensure_db()
    if current_admin():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        admin = db.get_admin_by_username(DB_PATH, username)

        if not admin or not check_password_hash(admin['password_hash'], password):
            flash('Invalid admin credentials.', 'danger')
            return render_template('login.html')

        session['admin_id'] = admin['id']
        session['admin_username'] = admin['username']
        session['admin_display_name'] = admin.get('display_name')
        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/settings')
@admin_required
def settings():
    return render_template('settings.html')


@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    ensure_db()
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        display_name = (request.form.get('display_name') or '').strip() or None

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('admin_register.html')

        existing_admin = db.get_admin_by_username(DB_PATH, username)
        if existing_admin:
            flash('That admin username is already in use.', 'danger')
            return render_template('admin_register.html')

        admin_id = db.add_admin(DB_PATH, username, generate_password_hash(password), display_name)
        session['admin_id'] = admin_id
        session['admin_username'] = username
        session['admin_display_name'] = display_name
        flash('Admin account created successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('admin_register.html')

# Register new person page
@app.route('/register')
@admin_required
def register_page():
    return render_template('register.html')


@app.route('/persons')
@admin_required
def persons_page():
    ensure_db()
    persons = db.get_all_persons_with_counts(DB_PATH)
    return render_template('persons.html', persons=persons)


@app.route('/person/<int:person_id>')
@admin_required
def person_detail_page(person_id):
    ensure_db()
    person = db.get_person_details(DB_PATH, person_id)
    if not person:
        flash('Person not found.', 'warning')
        return redirect(url_for('persons_page'))
    return render_template('person_detail.html', person=person)


@app.route('/person/<int:person_id>/update', methods=['POST'])
@admin_required
def update_person_page(person_id):
    ensure_db()
    person = db.get_person_by_id(DB_PATH, person_id)
    if not person:
        flash('Person not found.', 'warning')
        return redirect(url_for('persons_page'))

    name = request.form.get('name') or person.get('name')
    age = request.form.get('age')
    gender = request.form.get('gender')
    address = request.form.get('address')
    notes = request.form.get('notes')

    db.update_person(DB_PATH, person_id, name, int(age) if age else None, gender, address, notes)

    image_files = request.files.getlist('image')
    if not image_files:
        single_image = request.files.get('image')
        image_files = [single_image] if single_image else []
    image_files = [image for image in image_files if image and image.filename]

    if image_files:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("update_person_api")
        for index, image in enumerate(image_files, start=1):
            filename = Path(image.filename).name
            out_path = os.path.join('photos', f"{person_id}_{index}_{filename}")
            image.save(out_path)
            photo_id = db.add_photo(DB_PATH, person_id, out_path)
            faces = embedder.extract_embeddings(out_path)
            logger.info(f"Extracted {len(faces)} faces from {out_path}")
            for face_index, (emb, bbox, ratios) in enumerate(faces, start=1):
                logger.info(f"Face {face_index} embedding: {emb[:5] if emb is not None else 'None'} bbox: {bbox} ratios: {ratios}")
                db.add_embedding(DB_PATH, person_id, photo_id, emb, ratios, model=('insightface' if emb is not None else 'fallback'))

    fingerprint_files = request.files.getlist('fingerprint')
    if not fingerprint_files:
        single_fingerprint = request.files.get('fingerprint')
        fingerprint_files = [single_fingerprint] if single_fingerprint else []
    fingerprint_files = [image for image in fingerprint_files if image and image.filename]

    if fingerprint_files:
        Path('temp').mkdir(parents=True, exist_ok=True)
        for image in fingerprint_files:
            suffix = Path(image.filename or 'fingerprint.png').suffix or '.png'
            temp_file = tempfile.NamedTemporaryFile(delete=False, dir='temp', suffix=suffix)
            temp_path = temp_file.name
            temp_file.close()
            try:
                image.save(temp_path)
                fingerprint_template = identityUtility.extractFingerData(temp_path)
                db.add_fingerprint(DB_PATH, person_id, fingerprint_template)
            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    flash('Person updated successfully.', 'success')
    return redirect(url_for('person_detail_page', person_id=person_id))

# Compare page
@app.route('/compare')
def compare_page():
    return render_template('compare.html')
    
@app.route('/direct_compare', methods=['POST'])
def direct_compare():
    """
    Directly compare two images using InsightFace embedding and cosine similarity.
    Accepts form-data with 'image1' and 'image2' file fields.
    Returns JSON: {score: float, match: bool}
    """
    from backend.embedder import extract_embeddings
    from backend.compare import cosine_similarity
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("direct_compare_api")

    if 'image1' not in request.files or 'image2' not in request.files:
        return jsonify({'error': 'Both image1 and image2 files required'}), 400
    img1 = request.files['image1']
    img2 = request.files['image2']

    # Save temp files
    import tempfile
    tf1 = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    tf2 = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    img1.save(tf1.name)
    img2.save(tf2.name)

    # Extract embeddings
    emb1_faces = extract_embeddings(tf1.name)
    emb2_faces = extract_embeddings(tf2.name)

    # Clean up temp files
    try:
        import os
        os.remove(tf1.name)
        os.remove(tf2.name)
    except Exception:
        pass

    if not emb1_faces or not emb2_faces:
        return jsonify({'error': 'No face detected in one or both images'}), 400

    # Use first face in each image
    emb1 = emb1_faces[0][0]
    emb2 = emb2_faces[0][0]
    score = cosine_similarity(emb1, emb2)
    logger.info(f"Direct compare score: {score}")
    # Use threshold 0.2 for match (can be adjusted)
    match = score >= 0.2
    if match:
        message = "The photos are similar."
    else:
        message = "The photos are not similar."
    return jsonify({'score': score, 'match': match, 'message': message})
"""Minimal Flask API wrapper for backend functions.

Endpoints:
- POST /add_person : multipart/form-data with fields: name, age, gender, address, image(file)
- POST /compare : multipart/form-data with fields: image(file), topk (optional), threshold (optional)

This file is intended as a lightweight integration layer for the UI.
"""

@app.route('/add_person', methods=['POST'])
@admin_required
def add_person():
    # Expect multipart/form-data with 'image' and form fields
    name = request.form.get('name')
    if not name:
        return jsonify({'error': 'name required'}), 400
    age = request.form.get('age')
    gender = request.form.get('gender')
    address = request.form.get('address')
    image_files = request.files.getlist('image')
    if not image_files:
        single_image = request.files.get('image')
        image_files = [single_image] if single_image else []

    image_files = [image for image in image_files if image and image.filename]
    if not image_files:
        return jsonify({'error': 'at least one image file required'}), 400

    # simple API key enforcement: if FACIAL_API_KEY is set, require it via header or form
    if API_KEY:
        key = request.headers.get('X-API-KEY') or request.form.get('api_key')
        if key != API_KEY:
            return jsonify({'error': 'unauthorized'}), 401

    db.init_db(DB_PATH)
    person_id = db.add_person(DB_PATH, name, int(age) if age else None, gender, address, None)

    photo_ids = []
    embedding_ids = []
    saved_paths = []

    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("add_person_api")

    for image in image_files:
        filename = Path(image.filename).name
        out_path = os.path.join('photos', f"{person_id}_{len(saved_paths) + 1}_{filename}")
        image.save(out_path)
        saved_paths.append(out_path)
        photo_id = db.add_photo(DB_PATH, person_id, out_path)
        photo_ids.append(photo_id)

        faces = embedder.extract_embeddings(out_path)
        logger.info(f"Extracted {len(faces)} faces from {out_path}")
        for idx, (emb, bbox, ratios) in enumerate(faces):
            logger.info(f"Face {idx+1} embedding: {emb[:5] if emb is not None else 'None'} bbox: {bbox} ratios: {ratios}")
            eid = db.add_embedding(DB_PATH, person_id, photo_id, emb, ratios, model=('insightface' if emb is not None else 'fallback'))
            embedding_ids.append(eid)

    logger.info(f"Photo IDs stored: {photo_ids}")
    logger.info(f"Embedding IDs stored: {embedding_ids}")
    return jsonify({'person_id': person_id, 'photo_ids': photo_ids, 'embedding_ids': embedding_ids, 'photo_count': len(photo_ids)})


@app.route('/compare', methods=['POST'])
def compare_endpoint():
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("compare_api")

    if 'image' not in request.files:
        logger.error("No image file in request")
        return jsonify({'error': 'image file required'}), 400
    image = request.files['image']
    topk = int(request.form.get('topk', 5))
    threshold = float(request.form.get('threshold', 0.4))

    # save temporary query image
    qname = Path(image.filename).name
    qpath = os.path.join('photos', f"query_{qname}")
    image.save(qpath)

    logger.info(f"DB path: {DB_PATH}")
    logger.info(f"Query image path: {qpath}")

    faces = extract_embeddings(qpath)
    logger.info(f"Extracted {len(faces)} faces from query image {qpath}")
    for idx, (emb, bbox, ratios) in enumerate(faces):
        logger.info(f"Query face {idx+1} embedding: {emb[:5] if emb is not None else 'None'} bbox: {bbox} ratios: {ratios}")
    if not faces:
        logger.warning("No face detected in query image")
        return jsonify({'error': 'no face detected'}), 400

    candidates = db.get_all_embeddings(DB_PATH)
    logger.info(f"DB embeddings loaded: {len(candidates)}")
    for cidx, c in enumerate(candidates):
        # c = (embedding_id, person_id, photo_id, vector, ratios)
        person_id = c[1]
        embedding = c[3]
        ratios = c[4]
        logger.info(f"Candidate {cidx+1} person_id={person_id} embedding: {embedding[:5] if embedding is not None else 'None'} ratios: {ratios}")
    if not candidates:
        logger.warning("No embeddings in DB")
        return jsonify({'query': qpath, 'faces': []})

    def ratio_similarity(r1, r2):
        """Compute similarity between two ratio dicts (simple inverse L1 distance, normalized)."""
        if not r1 or not r2:
            return 0.0
        keys = set(r1.keys()) & set(r2.keys())
        if not keys:
            return 0.0
        dists = [abs(r1[k] - r2[k]) for k in keys]
        mean_dist = sum(dists) / len(dists) if dists else 1.0
        # Similarity: higher is better, 1/(1+mean_dist) in [0,1]
        return 1.0 / (1.0 + mean_dist)

    faces_out = []
    for face_idx, (query_emb, bbox, query_ratios) in enumerate(faces):
        scored_candidates = []
        for c in candidates:
            emb_id, person_id, photo_id, db_emb, db_ratios = c
            emb_sim = cmp.cosine_similarity(query_emb, db_emb)
            ratio_sim = ratio_similarity(query_ratios, db_ratios)
            # Weighted sum: embedding similarity (0.7), ratio similarity (0.3)
            combined_score = 0.7 * emb_sim + 0.3 * ratio_sim
            scored_candidates.append({
                'embedding_id': emb_id,
                'person_id': person_id,
                'photo_id': photo_id,
                'score': combined_score,
                'embedding_score': emb_sim,
                'ratio_score': ratio_sim
            })
        # Sort and filter by threshold
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        matches = [m for m in scored_candidates if m['score'] >= threshold][:topk]
        out = []
        for m in matches:
            p = db.get_person_by_id(DB_PATH, m['person_id'])
            photo_url = get_primary_face_photo_url(m['person_id'])
            logger.info(f"Match: person_id={m['person_id']}, name={p.get('name') if p else 'Unknown'}, score={m['score']}, emb_score={m['embedding_score']}, ratio_score={m['ratio_score']}")
            out.append({
                'person_id': m['person_id'],
                'name': p.get('name') if p else 'Unknown',
                'age': p.get('age') if p else '',
                'gender': p.get('gender') if p else '',
                'address': p.get('address') if p else '',
                'photo_url': photo_url,
                'score': m['score'],
                'embedding_score': m['embedding_score'],
                'ratio_score': m['ratio_score']
            })
        faces_out.append({'bbox': bbox, 'matches': out})

    # User-friendly summary message
    summary = "No similar faces found."
    for face in faces_out:
        if face['matches']:
            summary = "Similar faces found!"
            break

    return jsonify({'query': qpath, 'faces': faces_out, 'message': summary})


@app.route('/get_all_persons', methods=['GET'])
@admin_required
def get_all_persons():
    persons = db.get_all_persons_with_counts(DB_PATH)
    return jsonify(persons)


@app.route('/add_fingerprint', methods=['POST'])
@admin_required
def add_fingerprint():
    db.init_db(DB_PATH)
    person_id_raw = request.form.get("person_id")
    fingerprint_files = request.files.getlist("fingerprint")
    if not fingerprint_files:
        single_fingerprint = request.files.get("fingerprint")
        fingerprint_files = [single_fingerprint] if single_fingerprint else []

    if not person_id_raw:
        return jsonify({
            "status": "error",
            "message": "Person ID is required"
        }), 400

    try:
        person_id = int(person_id_raw)
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "Person ID must be a number"
        }), 400

    if not db.get_person_by_id(DB_PATH, person_id):
        return jsonify({
            "status": "error",
            "message": "Person not found"
        }), 404

    fingerprint_files = [image for image in fingerprint_files if image and image.filename]
    if not fingerprint_files:
        return jsonify({
            "status": "error",
            "message": "Fingerprint image required"
        }), 400

    Path('temp').mkdir(parents=True, exist_ok=True)
    fingerprint_ids = []

    try:
        for image in fingerprint_files:
            suffix = Path(image.filename or 'fingerprint.png').suffix or '.png'
            temp_file = tempfile.NamedTemporaryFile(delete=False, dir='temp', suffix=suffix)
            temp_path = temp_file.name
            temp_file.close()

            try:
                image.save(temp_path)
                fingerprint_template = identityUtility.extractFingerData(temp_path)
                fingerprint_id = db.add_fingerprint(DB_PATH, person_id, fingerprint_template)
                fingerprint_ids.append(fingerprint_id)
            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Unable to enroll fingerprint: {exc}"
        }), 500

    person = db.get_person_by_id(DB_PATH, person_id)
    person_details = db.get_person_details(DB_PATH, person_id) or person
    if person_details is not None:
        person_details['photo_url'] = get_primary_face_photo_url(person_id)
    return jsonify({
        "status": "success",
        "message": "Fingerprint enrolled successfully",
        "fingerprint_ids": fingerprint_ids,
        "fingerprint_count": len(fingerprint_ids),
        "person": person_details
    })

@app.route('/verify_fingerprint', methods=['POST'])
def verify_fingerprint():

    image = request.files.get("fingerprint")

    if not image:
        return jsonify({
            "match": False,
            "message": "Fingerprint image required"
        }), 400

    Path('temp').mkdir(parents=True, exist_ok=True)
    suffix = Path(image.filename or 'fingerprint.png').suffix or '.png'
    temp_file = tempfile.NamedTemporaryFile(delete=False, dir='temp', suffix=suffix)
    temp_path = temp_file.name
    temp_file.close()

    try:
        image.save(temp_path)
        probe_template = identityUtility.extractFingerData(temp_path)
    except Exception as exc:
        return jsonify({
            "match": False,
            "message": f"Unable to process fingerprint: {exc}"
        }), 500
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    cur.execute("""
        SELECT
            f.person_id,
            f.fingerprint_data,
            p.name,
            p.age,
            p.gender,
            p.address
        FROM fingerprints f
        JOIN persons p
            ON p.id = f.person_id
    """)

    rows = cur.fetchall()

    conn.close()

    best_score = 0
    best_person = None

    for row in rows:

        verify_result = (
            identityUtility.verifyFingerData(
                probe_template,
                row["fingerprint_data"]
            )
        )

        score = verify_result["score"]

        if verify_result["matched"] and score > best_score:
            best_score = score
            best_person = row

    if best_person is None:
        return jsonify({
            "match": False,
            "message": "No matching fingerprint found",
            "score": 0,
            "person": None
        })

    person_payload = {
        "person_id": best_person["person_id"],
        "name": best_person["name"],
        "age": best_person["age"],
        "gender": best_person["gender"],
        "address": best_person["address"],
        "photo_url": get_primary_face_photo_url(best_person["person_id"]),
    }

    return jsonify({
        "match": True,
        "person_id": best_person["person_id"],
        "name": best_person["name"],
        "score": best_score,
        "person": person_payload,
        "message": "Fingerprint matched successfully"
    })

@app.route('/register_thumb')
@admin_required
def register_thumb():
    return render_template('register_thumb.html')


@app.route('/compare_thumb')
def compare_thumb():
    return render_template('compare_thumb.html')





if __name__ == '__main__':
    # development server
    app.run(host='127.0.0.1', port=5000, debug=True)
