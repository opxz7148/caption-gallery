from logging import getLogger
import os
from platform import processor
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch

logger = getLogger(__name__)

class CaptionModel:
    
    def __init__(self, model_name="Salesforce/blip-image-captioning-large"):
        self.model_name = model_name
        # Load your pre-trained captioning model here (e.g., a transformer-based model)
        # This is a placeholder and should be replaced with actual model loading code
        self.model = None
        self.processor = None
        
        self.load_model(model_name)
        
    def load_model(self, model_name):
        try:
            logger.info("Loading BLIP model...")
            
            # Load processor
            self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
            if self.processor is None:
                raise Exception("Failed to load processor")
            logger.info("Processor loaded successfully")
            
            # Load model
            self.model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")
            if self.model is None:
                raise Exception("Failed to load model")
            logger.info("Model loaded successfully")
            
            # Move model to GPU if available
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = self.model.to(device)
            logger.info(f"Model moved to device: {device}")
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            # Set globals to None on failure
            self.processor = None
            self.model = None
            raise
        
        
    def generate_caption(self, image_path):
        # Implement the logic to generate a caption for the given image
        # This is a placeholder implementation and should be replaced with actual model inference
        if self.model is None or self.processor is None:
            logger.error("Model or processor not loaded")
            logger.info("Try to reload the model...")
            self.load_model(self.model_name)
            if self.model is None or self.processor is None:
                raise RuntimeError("Error: Failed to reload model")
    
        if not os.path.exists(image_path):
            logger.info(f"Image file not found: {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        try:
            image = Image.open(image_path).convert('RGB')
            logger.info(f"Image loaded successfully: {image.size}")
        except Exception as e:
            logger.error(f"Error loading image: {str(e)}")
            raise e

        try:
            inputs = self.processor(image, return_tensors="pt")
            logger.info("Image processed by processor")
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise e

        # Move inputs to same device as model
        try:
            device = next(self.model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            logger.info(f"Inputs moved to device: {device}")
        except Exception as e:
            logger.error(f"Error moving inputs to device: {str(e)}")
            raise e
        
        # Generate caption
        try:
            with torch.no_grad():
                out = self.model.generate(**inputs, max_length=50, num_beams=5)
            logger.info("Caption generated successfully")
        except Exception as e:
            logger.error(f"Error generating caption: {str(e)}")
            raise e
        
        try:
            caption = self.processor.decode(out[0], skip_special_tokens=True)
            logger.info(f"Caption decoded: {caption}")
            return caption if caption else "No caption generated"
        except Exception as e:
            logger.error(f"Error decoding caption: {str(e)}")
            raise e