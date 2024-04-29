
const language = document.querySelector('.language')
eventListeners()

function eventListeners(params) {
    language.addEventListener('click',cambiarLenguage ) 
}

// Leer estado del localstorage

//LENGUAJE

const eng = document.querySelectorAll('.eng')
const esp = document.querySelectorAll('.esp')
const balllang = document.querySelector('.ball-lang')
const engIndicator = document.querySelector('#eng')
const espIndicator = document.querySelector('#esp')

if (localStorage.getItem('LANGUAGE')) {     
    balllang.classList.add('ball-move')      
    espIndicator.classList.remove('langOn')       
    eng.forEach(element => {            
            element.classList.add('displayOn')          
                           })       
    esp.forEach(element => {
            element.classList.add('displayOff')                       
    }) 
} else { 
    engIndicator.classList.remove('langOn')  
balllang.classList.remove('ball-move')    
eng.forEach(element => {        
  element.classList.add('displayOff')       
 })     
esp.forEach(element => {                   
       element.classList.add('displayOn')
    }) 
}

//cambiar  lenguage

function cambiarLenguage(idioma) {    

console.log('click');
if (localStorage.getItem('LANGUAGE')) {  
    espIndicator.classList.add('langOn')
    engIndicator.classList.remove('langOn')      
    balllang.classList.remove('ball-move')    
    localStorage.removeItem('LANGUAGE', true)
    eng.forEach(element => {
        if (element.classList.contains('displayOn')) {
            element.classList.add('displayOff')
            element.classList.remove("displayOn")                
          }   
            
    })    
    esp.forEach(element => {
         if (element.classList.contains('displayOff') ) { 
            element.classList.add('displayOn')            
            element.classList.remove("displayOff")   
        }  
    })   
} else {
    engIndicator.classList.add('langOn') 
    espIndicator.classList.remove('langOn')  
    balllang.classList.add('ball-move')
    localStorage.setItem('LANGUAGE', true)
    eng.forEach(element => {
        
      element.classList.add('displayOn')     
     element.classList.remove('displayOff')  
            
                             
    })
     
   esp.forEach(element => {
                   
           element.classList.remove('displayOn')
           element.classList.add('displayOff')
        }
         )     
}                   
   }



