import csv

student_related = 0
total_rows = 0

with open("grounded_cafe_orders.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_rows += 1
        if row["item_name"] in ("Student Meal", "Student Drink") or row["discount_name"] == "Student Discount":
            student_related += 1

print(f"Total rows: {total_rows}")
print(f"Student-related rows: {student_related}")
print(f"Proportion: {student_related / total_rows:.1%}")