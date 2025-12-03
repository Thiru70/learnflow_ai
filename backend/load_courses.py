#!/usr/bin/env python3
"""
Load courses from CSV into MongoDB
"""

import pandas as pd
from mongoengine import connect
from models.course import Course

# MongoDB connection
connect('learning_system_dev', host='mongodb://localhost:27017/')

def load_courses():
    print("Loading courses from CSV...")
    
    # Clear existing courses
    Course.objects().delete()
    print("Cleared existing courses")
    
    # Load from CSV
    df = pd.read_csv('data/courses.csv')
    loaded_count = 0
    
    for _, row in df.iterrows():
        try:
            course = Course(
                course_id=str(row['id']),
                title=row['title'],
                description=row['description'],
                type=row['type'],
                difficulty=row['difficulty'],
                duration=row['duration'],
                tags=row['tags'],
                category=row['category'],
                author=row['author'],
                rating=float(row['rating']),
                likes=int(row['likes']),
                url=row['url']
            )
            course.save()
            loaded_count += 1
            print(f"Loaded course: {row['title']}")
            
        except Exception as e:
            print(f"Error loading course {row['id']}: {e}")
            continue
    
    print(f"\nSuccessfully loaded {loaded_count} courses")
    print(f"Total courses in database: {Course.objects().count()}")

if __name__ == '__main__':
    load_courses()