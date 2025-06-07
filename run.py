from app import create_app

app = create_app()

if __name__ == '__main__':
    print("✅ FLASK SE ESTÁ EJECUTANDO")
    app.run(debug=True)
