import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import beta, norm

# make font larger
plt.rcParams.update({'font.size': 14})



def plot_pdfs(starting_age=18, n_points=1000):
    # Age PDF (Beta distribution, scaled)
    age_x = np.linspace(starting_age, 70, n_points)
    age_pdf = beta.pdf((age_x - starting_age) / (70 - starting_age), 2, 8) / (70 - starting_age)
    plt.figure()
    plt.plot(age_x, age_pdf)
    plt.title('Age Distribution')
    plt.xlabel('Age (Years)')
    plt.ylabel('Probability')
    plt.savefig('age_pdf.png')
    plt.close()

    # Activity PDF (Normal distribution)
    activity_x = np.linspace(0.5, 2.5, n_points)
    activity_pdf = norm.pdf(activity_x, 1.5, 1/6)
    plt.figure()
    plt.plot(activity_x, activity_pdf)
    plt.title('Exercise Activity Distribution ')
    plt.xlabel('Hours of Exercise per Day')
    plt.ylabel('Probability')
    plt.savefig('activity_pdf.png')
    plt.close()

    # Body size PDF (Normal, male and female)
    body_x = np.linspace(30, 120, n_points)
    # Female
    body_pdf_f = norm.pdf(body_x, 67.5, 13.8)
    # Male
    body_pdf_m = norm.pdf(body_x, 80.3, 13.5)
    plt.figure()
    plt.plot(body_x, body_pdf_f, label='Female')
    plt.plot(body_x, body_pdf_m, label='Male')
    plt.title('Body Size Distribution')
    plt.xlabel('Body Mass (kg)')
    plt.ylabel('Probability')
    plt.legend()
    plt.show()

# Call the function to generate and save the plots
plot_pdfs()