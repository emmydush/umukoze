from app import app, db, User, Worker, Employer
from flask import url_for

with app.app_context():
    # Get a test user
    worker_user = User.query.filter_by(user_type='worker').first()
    if worker_user:
        print(f'Testing with worker user: {worker_user.email}')
        
        # Check worker profile
        worker = Worker.query.filter_by(user_id=worker_user.id).first()
        print(f'Worker profile: {worker}')
        
        if worker:
            # Test profile completion check
            from app import calculate_profile_completion
            completion = calculate_profile_completion(worker)
            print(f'Profile completion: {completion}%')
            
            # Test dashboard logic
            try:
                from app import check_profile_completion
                is_complete = check_profile_completion(worker)
                print(f'Profile is complete: {is_complete}')
                
                if not is_complete:
                    print('Would redirect to worker_complete_profile')
                else:
                    print('Would render worker_dashboard.html')
                    
            except Exception as e:
                print(f'Error in profile completion: {e}')
                import traceback
                traceback.print_exc()
