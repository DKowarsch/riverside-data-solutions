// Language data
const translations = {
    en: {
        siteTitle: "Riverside Data Solutions",
        aboutTitle: "About the Company",
        aboutDescription1: "Welcome to Riverside Data Solutions! Founded in early 2025, this company has been a dream of mine for years.",
        aboutDescription2: "We have a dedicated team of data engineers, data analysts, and data scientists to deliver comprehensive solutions.",
        aboutDescription3: "Our mission is to empower your business with data-driven insights and strategies.",
        servicesTitle: "Our Services",
        servicesList: [
            "Data Engineering: Building robust data pipelines.",
            "Data Analytics: Insightful dashboards and reports.",
            "Data Science: Predictive modeling and machine learning."
        ],
        contactTitle: "Contact Us",
        contactInfo: [
            "Email: data_solutions_llc@yahoo.com",
            "Phone: +1 (951) 785-2481",
            "Location: Riverside, California, USA"
        ],
        footerText: "© 2025 Riverside Data Solutions"
    },
    es: {
        siteTitle: "Soluciones de Datos Riverside",
        aboutTitle: "Sobre la Empresa",
        aboutDescription1: "¡Bienvenido a Soluciones de Datos Riverside! Fundada a principios de 2025, esta empresa ha sido un sueño mío durante años.",
        aboutDescription2: "Contamos con un equipo dedicado de ingenieros de datos, analistas de datos y científicos de datos para ofrecer soluciones completas.",
        aboutDescription3: "Nuestra misión es empoderar a su empresa con conocimientos y estrategias basadas en datos.",
        servicesTitle: "Nuestros Servicios",
        servicesList: [
            "Ingeniería de Datos: Construcción de canalizaciones de datos robustas.",
            "Análisis de Datos: Tableros e informes perspicaces.",
            "Ciencia de Datos: Modelado predictivo y aprendizaje automático."
        ],
        contactTitle: "Contáctenos",
        contactInfo: [
            "Correo electrónico: data_solutions_llc@yahoo.com",
            "Teléfono: +1 (951) 785-2481",
            "Dirección: Riverside, California, USA"
        ],
        footerText: "© 2025 Soluciones de Datos Riverside"
    },
    zh: {
        siteTitle: "河滨数据解决方案",
        aboutTitle: "关于公司",
        aboutDescription1: "欢迎来到河滨数据解决方案！该公司成立于2025年初，这家公司是我多年来的梦想。",
        aboutDescription2: "我们拥有一支由数据工程师、数据分析师和数据科学家组成的专业团队，提供全面的解决方案。",
        aboutDescription3: "我们的使命是通过数据驱动的洞察力和策略赋能您的业务。",
        servicesTitle: "我们的服务",
        servicesList: [
            "数据工程：构建强大的数据管道。",
            "数据分析：有洞察力的仪表板和报告。",
            "数据科学：预测建模和机器学习。"
        ],
        contactTitle: "联系我们",
        contactInfo: [
            "电子邮件: data_solutions_llc@yahoo.com",
            "电话: +1 (951) 785-2481",
            "地址: Riverside, Calinfornia, USA"
        ],
        footerText: "© 2025 河滨数据解决方案"
    }
};

// Function to update content based on language
function updateContent(language) {
    const langData = translations[language];
    document.getElementById("site-title").textContent = langData.siteTitle;
    document.getElementById("about-title").textContent = langData.aboutTitle;
    document.getElementById("about-description-1").textContent = langData.aboutDescription1;
    document.getElementById("about-description-2").textContent = langData.aboutDescription2;
    document.getElementById("about-description-3").textContent = langData.aboutDescription3;
    document.getElementById("services-title").textContent = langData.servicesTitle;

    // Update services list
    const servicesList = document.getElementById("services-list");
    servicesList.innerHTML = "";
    langData.servicesList.forEach(service => {
        const li = document.createElement("li");
        li.textContent = service;
        servicesList.appendChild(li);
    });

    document.getElementById("contact-title").textContent = langData.contactTitle;

    // Update contact info list
    const contactInfo = document.getElementById("contact-info");
    contactInfo.innerHTML = "";
    langData.contactInfo.forEach(info => {
        const li = document.createElement("li");
        li.textContent = info;
        contactInfo.appendChild(li);
    });

    document.getElementById("footer-text").textContent = langData.footerText;
}

// Event listeners for language buttons
document.querySelectorAll(".lang-btn").forEach(button => {
    button.addEventListener("click", () => {
        const selectedLanguage = button.getAttribute("data-lang");
        updateContent(selectedLanguage);
    });
});

// Set default language to English
updateContent("en");