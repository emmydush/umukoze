from app import app, db, User, Worker, Employer

with app.app_context():
    # Check existing users
    users = User.query.all()
    print(f'Total users: {len(users)}')
    
    for user in users:
        print(f'User: {user.email}, Type: {user.user_type}, Active: {user.is_active}')
        
        if user.user_type == 'worker':
            worker = Worker.query.filter_by(user_id=user.id).first()
            print(f'  Worker profile exists: {worker is not None}')
        elif user.user_type == 'employer':
            employer = Employer.query.filter_by(user_id=user.id).first()
            print(f'  Employer profile exists: {employer is not None}')
