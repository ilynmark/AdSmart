import base64
import io
import os

import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

from adsmart import generate_advertisement

_, ax = plt.subplots()
ax.set_ylim([0, 100])
GENERATED_DATA = {}
app = Flask(__name__)
app.secret_key = "adsmart"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.abspath(
    "database/prompts.db"
)
db = SQLAlchemy(app)


class Prompts(db.Model):
    uID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    orga = db.Column(db.String(50))
    kw = db.Column(db.String(200))
    length = db.Column(db.String(20))
    tone = db.Column(db.String(20))
    gen_prompt = db.Column(db.String(200))
    rating = db.Column(db.Integer, default=0)

    def show_info(self):
        """Prints the attributes of a Prompts instance."""
        print(
            f"""
            ID: {self.uID}, 
            Name: {self.name}, 
            Organization: {self.orga}, 
            Key-Words: {self.kw}, 
            Length: {self.length},
            Tone: {self.tone},
            Prompt: {self.gen_prompt},
            Rating: {self.rating}
            """
        )


def show_db():
    """Prints the information of all prompts in the database."""
    print("-" * 100)

    # Retrieve all instances of the User model
    all_prompts = Prompts.query.all()

    # Loop through the instances and print their attributes
    for prompt in all_prompts:
        prompt.show_info()

    print("-" * 100)


@app.route("/")
@app.route("/home")
def home():
    """Renders the home page template."""
    global GENERATED_DATA
    GENERATED_DATA = {}

    return render_template("index.html")


@app.route("/features")
def features():
    """Renders the features page template."""
    return render_template("features.html")


@app.route("/about")
def about():
    """Renders the about page template."""
    return render_template("about.html")


@app.route("/form", methods=["GET", "POST"])
def form():
    """Handles the form submission and redirects to ad_prompts page."""
    if request.method == "POST":
        name = request.form["name"].replace("/", "")
        orga = request.form["orga"].replace("/", "")
        kw = request.form["kw"].replace("/", "")

        if not (3 <= len(kw.split(", ")) <= 20):
            flash("Enter your keywords (min 3, max 20)")
            return render_template("form.html")
        if orga == "":
            orga = "0"

        length = request.form["length"]

        return redirect(
            url_for("ad_prompts", name=name, orga=orga, kw=kw, length=length)
        )

    return render_template("form.html")


@app.route("/ad_prompts/<name>/<orga>/<kw>/<length>")
def ad_prompts(name, orga, kw, length):
    """Generates advertisement prompts based on user input and renders the ad_prompts page."""
    global GENERATED_DATA

    gen_prompts, tones = generate_advertisement(name, kw, length, orga)
    GENERATED_DATA = {
        "name": name,
        "orga": orga,
        "kw": kw,
        "length": length,
        "tones": tones,
        "gen_prompts": gen_prompts,
        "gen_prompt": ""
    }

    return render_template("ad_prompts.html", data=GENERATED_DATA)


@app.route("/take_prompt/<int:index>")
def take_prompt(index):
    """Adds a new prompt to the database and redirects to the final_page."""
    if GENERATED_DATA["gen_prompt"] == "":
        gen_prompt = GENERATED_DATA["gen_prompts"][index]
        GENERATED_DATA["gen_prompt"] = gen_prompt
    
    new_prompt = Prompts(
        name=GENERATED_DATA["name"],
        orga=GENERATED_DATA["orga"],
        kw=GENERATED_DATA["kw"],
        length=GENERATED_DATA["length"],
        tone=GENERATED_DATA["tones"][index],
        gen_prompt=GENERATED_DATA["gen_prompt"],
    )

    db.session.add(new_prompt)
    db.session.commit()

    return redirect(url_for("final_page"))


@app.route("/final_page", methods=["GET", "POST"])
def final_page():
    """Renders the final_page template and handles the rating submission."""
    rating = 0
    if request.method == "POST":
        if 'rate' in request.form:
            rating = int(request.form['rate'])

        promopt = Prompts.query.filter_by(gen_prompt=GENERATED_DATA["gen_prompt"]).first()
        promopt.rating = rating
        db.session.commit()

        return render_template("final_page.html", prompt=GENERATED_DATA["gen_prompt"], star=rating)

    return render_template("final_page.html", prompt=GENERATED_DATA["gen_prompt"], star=rating)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    """Renders the admin_login page and handles the login process."""
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]
        if name == "admin" and password == "admin":
            return redirect(url_for("dashboard"))
        else:
            flash("Unauthorized access!")
            return render_template("admin_login.html")

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def dashboard():
    """Renders the dashboard page with statistical information."""
    global ax
    # TODO: optimize this part, it's too long
    used_kws = {}
    used_lengths = {}
    kw_lengths = []
    tones = {"Persuasive": 0, "Exciting": 0, "Funny": 0}

    all_prompts = Prompts.query.all()
    for prompt in all_prompts:
        kws = prompt.kw.split(", ")
        kw_lengths.append(len(kws))
        length = prompt.length

        for kw in kws:
            if not kw in used_kws:
                used_kws[kw] = 1
            else:
                used_kws[kw] += 1

        if not length in used_lengths:
            used_lengths[length] = 1
        else:
            used_lengths[length] += 1

        tone = prompt.tone.capitalize()
        tones[tone] += 1

    mean_kw_lengths = int(np.mean(kw_lengths))
    popular_prompt_length = max(used_lengths, key=lambda key: used_lengths[key])
    most_common_kw = max(used_kws, key=lambda key: used_kws[key])
    avg_rating = np.mean([prompt.rating for prompt in Prompts.query.all() if prompt.rating != 0])
    ####

    bar_labels = ["Persuasive", "Exciting", "Funny"]
    bar_values = [tones[tone] for tone in bar_labels]
    bar_values_rel = [x/sum(bar_values)*100 for x in bar_values]
    
    ax.bar(bar_labels, bar_values_rel, color="C0")
    ax.set_title("Percentage per Tone", size=14)
    ax.set_ylabel("User Count")
    for i, num in enumerate(bar_values_rel):
        ax.text(i, num, f"{np.round(num, 2)}%", ha='center')

    tones_bar = io.BytesIO()
    plt.savefig(tones_bar, format="png")
    tones_bar.seek(0)
    tones_bar_base64 = base64.b64encode(tones_bar.getvalue()).decode()

    return render_template(
        "dashboard.html",
        tones_bar=tones_bar_base64,
        mean_kw_lengths=mean_kw_lengths,
        popular_prompt_length=popular_prompt_length,
        most_common_kw=most_common_kw,
        avg_rating=np.round(avg_rating, 1),
    )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        show_db()

    app.run(debug=True, port=5000)
