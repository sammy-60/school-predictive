from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route("/login", methods=["GET", "POST"])
def login():
    message = None
    if request.method == "POST":
        email = request.form.get("email","").strip()
        password = request.form.get("password","")
        # TODO: replace with real DB check
        if email == "admin@example.com" and password == "admin123":
            return redirect(url_for("dashboard"))
        message = "Invalid email or password"
    return render_template("login.html", message=message)

@app.route("/dashboard")
def dashboard():
    return "<h2>Dashboard</h2><p>Coming soon…</p>"

@app.route("/")
def home():
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
