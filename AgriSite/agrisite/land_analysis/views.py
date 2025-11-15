import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Set the backend before importing pyplot
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Avg, Count, F, Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from .models import *
from .utils import generate_land_analysis_charts
from .forms import CustomUserCreationForm, UserProfileForm, ContactForm

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'👋 Welcome back, {self.request.user.first_name or self.request.user.username}!')
        return response

def custom_logout(request):
    """Custom logout view that works with GET requests and shows notifications"""
    if request.user.is_authenticated:
        messages.info(request, '👋 You have been successfully logged out. See you soon!')
    logout(request)
    return redirect('home')

def home(request):
    """Home page with overview"""
    try:
        total_land_holders = LandHolder.objects.count()
        total_parcels = LandParcel.objects.count()
        total_cultivated_area = LandParcel.objects.aggregate(Sum('cultivated_area'))['cultivated_area__sum'] or 0
        
        # Recent activities
        recent_parcels = LandParcel.objects.select_related('land_holder', 'land_holder__region').order_by('-created_at')[:5]
        
        # Enhanced statistics for the new homepage
        regions = Region.objects.all()
        soil_types = LandParcel.SOIL_TYPES
        crops = Crop.objects.all()[:10]
        years = CroppingPattern.objects.dates('year', 'year').distinct().order_by('-year')[:5]
        
        context = {
            'total_land_holders': total_land_holders,
            'total_parcels': total_parcels,
            'total_cultivated_area': total_cultivated_area,
            'recent_parcels': recent_parcels,
            'regions': regions,
            'soil_types': soil_types,
            'crops': crops,
            'years': [year.year for year in years],
        }
    except Exception as e:
        # Handle case when database is empty
        context = {
            'total_land_holders': 0,
            'total_parcels': 0,
            'total_cultivated_area': 0,
            'recent_parcels': [],
            'regions': [],
            'soil_types': [],
            'crops': [],
            'years': [],
        }
    
    return render(request, 'land_analysis/home.html', context)

def signup(request):
    """User registration/signup view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log the user in after registration
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'🎉 Welcome to AgriSite, {user.first_name}! Your account has been created successfully.')
                return redirect('dashboard')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'title': 'Sign Up - AgriSite'
    }
    return render(request, 'registration/signup.html', context)

@login_required
def profile(request):
    """User profile management"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'form': form,
        'title': 'My Profile - AgriSite'
    }
    return render(request, 'land_analysis/profile.html', context)

def contact(request):
    """Contact form view"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Here you would typically send an email
            # For now, we'll just show a success message
            messages.success(request, '✅ Thank you for your message! We will get back to you soon.')
            return redirect('home')
    else:
        form = ContactForm()
    
    context = {
        'form': form,
        'title': 'Contact Us - AgriSite'
    }
    return render(request, 'land_analysis/contact.html', context)

@login_required
def dashboard(request):
    """Main dashboard with analytics"""
    try:
        # Basic statistics
        stats = {
            'total_land_holders': LandHolder.objects.count(),
            'total_parcels': LandParcel.objects.count(),
            'total_cultivated_area': LandParcel.objects.aggregate(Sum('cultivated_area'))['cultivated_area__sum'] or 0,
            'avg_productivity': LandAnalysis.objects.aggregate(Avg('productivity_score'))['productivity_score__avg'] or 0,
        }
        
        # Land distribution by region
        region_data = LandParcel.objects.values(
            'land_holder__region__name', 'land_holder__region__id'
        ).annotate(
            total_area=Sum('total_area'),
            parcel_count=Count('id')
        ).order_by('-total_area')
        
        # Irrigation system distribution
        irrigation_data = IrrigationSystem.objects.values(
            'system_type'
        ).annotate(
            count=Count('id')
        )
        
        # Crop pattern analysis
        crop_data = CroppingPattern.objects.values(
            'crop__name', 'crop__id'
        ).annotate(
            total_area=Sum('area_allocated'),
            avg_yield=Avg('yield_amount')
        ).order_by('-total_area')[:10]
        
        # Generate charts
        charts = generate_land_analysis_charts()
        
        # Additional data for enhanced dashboard
        regions = Region.objects.all()
        soil_types = LandParcel.SOIL_TYPES
        crops = Crop.objects.all()
        years = CroppingPattern.objects.dates('year', 'year').distinct().order_by('-year')[:5]
        
    except Exception as e:
        # Handle empty database case
        stats = {
            'total_land_holders': 0,
            'total_parcels': 0,
            'total_cultivated_area': 0,
            'avg_productivity': 0,
        }
        region_data = []
        irrigation_data = []
        crop_data = []
        charts = {}
        regions = []
        soil_types = []
        crops = []
        years = []
    
    context = {
        'stats': stats,
        'region_data': list(region_data),
        'irrigation_data': list(irrigation_data),
        'crop_data': list(crop_data),
        'charts': charts,
        'regions': regions,
        'soil_types': soil_types,
        'crops': crops,
        'years': [year.year for year in years],
    }
    return render(request, 'land_analysis/dashboard.html', context)

@login_required
def land_parcel_list(request):
    """List all land parcels"""
    try:
        parcels = LandParcel.objects.select_related('land_holder', 'land_holder__region').prefetch_related('irrigation')
        
        # Filtering
        region_filter = request.GET.get('region')
        soil_filter = request.GET.get('soil_type')
        
        if region_filter:
            parcels = parcels.filter(land_holder__region_id=region_filter)
        if soil_filter:
            parcels = parcels.filter(soil_type=soil_filter)
        
        regions = Region.objects.all()
        
        # Calculate additional statistics for enhanced view
        total_area = parcels.aggregate(Sum('total_area'))['total_area__sum'] or 0
        cultivated_area = parcels.aggregate(Sum('cultivated_area'))['cultivated_area__sum'] or 0
        unique_crops = CroppingPattern.objects.filter(land_parcel__in=parcels).values('crop').distinct().count()
        
    except Exception as e:
        parcels = LandParcel.objects.none()
        regions = Region.objects.none()
        total_area = 0
        cultivated_area = 0
        unique_crops = 0
    
    context = {
        'parcels': parcels,
        'regions': regions,
        'soil_types': LandParcel.SOIL_TYPES,
        'total_area': total_area,
        'cultivated_area': cultivated_area,
        'unique_crops': unique_crops,
    }
    return render(request, 'land_analysis/land_parcel_list.html', context)

@login_required
def land_parcel_detail(request, pk):
    """Detail view for a land parcel"""
    try:
        parcel = get_object_or_404(
            LandParcel.objects.select_related(
                'land_holder', 
                'land_holder__region'
            ).prefetch_related(
                'irrigation',
                'cropping_patterns',
                'cropping_patterns__crop',
                'analyses'
            ), 
            pk=pk
        )
        
        # Cropping pattern history
        cropping_history = parcel.cropping_patterns.select_related('crop').order_by('year', 'season')
        
        # Analysis data
        analyses = parcel.analyses.order_by('-analysis_date')
        
        # Calculate cultivation percentage
        cultivation_percentage = (parcel.cultivated_area / parcel.total_area * 100) if parcel.total_area > 0 else 0
        
    except LandParcel.DoesNotExist:
        return render(request, 'land_analysis/404.html', status=404)
    
    context = {
        'parcel': parcel,
        'cropping_history': cropping_history,
        'analyses': analyses,
        'cultivation_percentage': round(cultivation_percentage, 1),
    }
    return render(request, 'land_analysis/land_parcel_detail.html', context)

@login_required
def analysis_reports(request):
    """Advanced analysis and reports"""
    try:
        # Land holding analysis
        land_holding_analysis = LandHolder.objects.values(
            'ownership_type'
        ).annotate(
            count=Count('id'),
            total_land=Sum('parcels__total_area'),
            avg_parcels=Avg('parcels__id', distinct=True)
        )
        
        # Irrigation efficiency analysis
        irrigation_efficiency = IrrigationSystem.objects.values(
            'system_type'
        ).annotate(
            avg_efficiency=Avg('efficiency_rating'),
            avg_water_usage=Avg('annual_water_usage')
        )
        
        # Crop productivity analysis
        crop_productivity = CroppingPattern.objects.values(
            'crop__name', 'crop__crop_type', 'crop__id'
        ).annotate(
            total_area=Sum('area_allocated'),
            avg_yield=Avg('yield_amount'),
            total_revenue=Sum('revenue')
        ).order_by('-total_revenue')
        
        # Year-wise production trend
        production_trend = CroppingPattern.objects.values(
            'year'
        ).annotate(
            total_yield=Sum('yield_amount'),
            total_revenue=Sum('revenue')
        ).order_by('year')
        
        # Additional data for enhanced analysis reports
        regions = Region.objects.all()
        soil_types = LandParcel.SOIL_TYPES
        
        # Calculate additional metrics
        total_land_area = LandParcel.objects.aggregate(Sum('total_area'))['total_area__sum'] or 0
        total_cultivated_area = LandParcel.objects.aggregate(Sum('cultivated_area'))['cultivated_area__sum'] or 0
        
    except Exception as e:
        land_holding_analysis = []
        irrigation_efficiency = []
        crop_productivity = []
        production_trend = []
        regions = []
        soil_types = []
        total_land_area = 0
        total_cultivated_area = 0
    
    context = {
        'land_holding_analysis': list(land_holding_analysis),
        'irrigation_efficiency': list(irrigation_efficiency),
        'crop_productivity': list(crop_productivity),
        'production_trend': list(production_trend),
        'regions': regions,
        'soil_types': soil_types,
        'total_land_area': total_land_area,
        'total_cultivated_area': total_cultivated_area,
    }
    return render(request, 'land_analysis/analysis_reports.html', context)

@login_required
def api_land_stats(request):
    """API endpoint for land statistics"""
    try:
        # Get filter parameters
        region_id = request.GET.get('region')
        soil_type = request.GET.get('soil_type')
        time_period = request.GET.get('time_period', '30d')
        
        # Base querysets
        land_parcels = LandParcel.objects.all()
        irrigation_systems = IrrigationSystem.objects.all()
        cropping_patterns = CroppingPattern.objects.all()
        
        # Apply filters
        if region_id:
            land_parcels = land_parcels.filter(land_holder__region_id=region_id)
            irrigation_systems = irrigation_systems.filter(land_parcel__land_holder__region_id=region_id)
            cropping_patterns = cropping_patterns.filter(land_parcel__land_holder__region_id=region_id)
            
        if soil_type:
            land_parcels = land_parcels.filter(soil_type=soil_type)
            irrigation_systems = irrigation_systems.filter(land_parcel__soil_type=soil_type)
            cropping_patterns = cropping_patterns.filter(land_parcel__soil_type=soil_type)
        
        # Land distribution by soil type
        soil_distribution = land_parcels.values('soil_type').annotate(
            count=Count('id'),
            total_area=Sum('total_area')
        )
        
        # Irrigation system distribution
        irrigation_distribution = irrigation_systems.values('system_type').annotate(
            count=Count('id'),
            avg_efficiency=Avg('efficiency_rating')
        )
        
        # Crop type distribution
        crop_distribution = cropping_patterns.values('crop__crop_type').annotate(
            total_area=Sum('area_allocated'),
            avg_yield=Avg('yield_amount')
        )
        
        # Region statistics
        region_stats = LandParcel.objects.values('land_holder__region__name').annotate(
            parcel_count=Count('id'),
            total_area=Sum('total_area'),
            cultivated_area=Sum('cultivated_area')
        )
        
        return JsonResponse({
            'soil_distribution': list(soil_distribution),
            'irrigation_distribution': list(irrigation_distribution),
            'crop_distribution': list(crop_distribution),
            'region_stats': list(region_stats),
            'status': 'success'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def region_analysis(request, region_id):
    """Detailed analysis for a specific region"""
    region = get_object_or_404(Region, pk=region_id)
    
    try:
        # Region statistics
        region_stats = LandParcel.objects.filter(
            land_holder__region=region
        ).aggregate(
            total_parcels=Count('id'),
            total_area=Sum('total_area'),
            avg_parcel_size=Avg('total_area'),
            cultivated_percentage=Avg('cultivated_area') / Avg('total_area') * 100
        )
        
        # Top crops in region
        top_crops = CroppingPattern.objects.filter(
            land_parcel__land_holder__region=region
        ).values(
            'crop__name', 'crop__id'
        ).annotate(
            total_area=Sum('area_allocated'),
            avg_yield=Avg('yield_amount'),
            total_revenue=Sum('revenue')
        ).order_by('-total_area')[:10]
        
        # Soil type distribution in region
        soil_distribution = LandParcel.objects.filter(
            land_holder__region=region
        ).values('soil_type').annotate(
            count=Count('id'),
            total_area=Sum('total_area')
        )
        
        # Irrigation systems in region
        irrigation_systems = IrrigationSystem.objects.filter(
            land_parcel__land_holder__region=region
        ).values('system_type').annotate(
            count=Count('id'),
            avg_efficiency=Avg('efficiency_rating')
        )
        
    except Exception as e:
        region_stats = {}
        top_crops = []
        soil_distribution = []
        irrigation_systems = []
    
    context = {
        'region': region,
        'region_stats': region_stats,
        'top_crops': list(top_crops),
        'soil_distribution': list(soil_distribution),
        'irrigation_systems': list(irrigation_systems),
    }
    
    return render(request, 'land_analysis/region_analysis.html', context)

@login_required
def crop_analysis(request, crop_id):
    """Detailed analysis for a specific crop"""
    crop = get_object_or_404(Crop, pk=crop_id)
    
    try:
        # Crop statistics
        crop_stats = CroppingPattern.objects.filter(
            crop=crop
        ).aggregate(
            total_area=Sum('area_allocated'),
            total_yield=Sum('yield_amount'),
            avg_yield_per_hectare=Avg('yield_amount') / Avg('area_allocated'),
            total_revenue=Sum('revenue'),
            avg_revenue_per_hectare=Avg('revenue') / Avg('area_allocated')
        )
        
        # Regional distribution of crop
        regional_distribution = CroppingPattern.objects.filter(
            crop=crop
        ).values(
            'land_parcel__land_holder__region__name',
            'land_parcel__land_holder__region__id'
        ).annotate(
            area=Sum('area_allocated'),
            yield_amount=Sum('yield_amount'),
            revenue=Sum('revenue')
        ).order_by('-area')
        
        # Seasonal performance
        seasonal_performance = CroppingPattern.objects.filter(
            crop=crop
        ).values('season').annotate(
            avg_yield=Avg('yield_amount'),
            avg_revenue=Avg('revenue'),
            total_area=Sum('area_allocated')
        )
        
        # Yearly trend
        yearly_trend = CroppingPattern.objects.filter(
            crop=crop
        ).values('year').annotate(
            total_yield=Sum('yield_amount'),
            total_revenue=Sum('revenue'),
            total_area=Sum('area_allocated')
        ).order_by('year')
        
    except Exception as e:
        crop_stats = {}
        regional_distribution = []
        seasonal_performance = []
        yearly_trend = []
    
    context = {
        'crop': crop,
        'crop_stats': crop_stats,
        'regional_distribution': list(regional_distribution),
        'seasonal_performance': list(seasonal_performance),
        'yearly_trend': list(yearly_trend),
    }
    
    return render(request, 'land_analysis/crop_analysis.html', context)

@login_required
def export_data(request, data_type):
    """Export data in various formats"""
    try:
        if data_type == 'land_parcels':
            data = LandParcel.objects.all().values(
                'parcel_id', 'total_area', 'cultivated_area', 'soil_type',
                'land_holder__name', 'land_holder__region__name'
            )
            filename = 'land_parcels'
        elif data_type == 'cropping_patterns':
            data = CroppingPattern.objects.all().values(
                'crop__name', 'year', 'season', 'area_allocated', 
                'yield_amount', 'revenue', 'land_parcel__parcel_id'
            )
            filename = 'cropping_patterns'
        elif data_type == 'irrigation_systems':
            data = IrrigationSystem.objects.all().values(
                'system_type', 'efficiency_rating', 'annual_water_usage',
                'land_parcel__parcel_id'
            )
            filename = 'irrigation_systems'
        elif data_type == 'comprehensive_report':
            # Generate comprehensive report
            return generate_comprehensive_report(request)
        else:
            return JsonResponse({'error': 'Invalid data type'}, status=400)
        
        # Convert to DataFrame for better formatting
        df = pd.DataFrame(list(data))
        
        # Determine response format
        format_type = request.GET.get('format', 'json')
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            df.to_csv(response, index=False)
            return response
        elif format_type == 'excel':
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
            df.to_excel(response, index=False)
            return response
        else:
            # Default to JSON
            response = JsonResponse(list(data), safe=False)
            response['Content-Disposition'] = f'attachment; filename="{filename}.json"'
            return response
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def generate_comprehensive_report(request):
    """Generate a comprehensive PDF report"""
    try:
        # This would typically generate a PDF using a library like ReportLab
        # For now, return a JSON response with comprehensive data
        
        comprehensive_data = {
            'summary': {
                'total_land_holders': LandHolder.objects.count(),
                'total_parcels': LandParcel.objects.count(),
                'total_cultivated_area': LandParcel.objects.aggregate(Sum('cultivated_area'))['cultivated_area__sum'] or 0,
                'total_revenue': CroppingPattern.objects.aggregate(Sum('revenue'))['revenue__sum'] or 0,
            },
            'land_analysis': list(LandHolder.objects.values('ownership_type').annotate(
                count=Count('id'),
                total_land=Sum('parcels__total_area')
            )),
            'crop_analysis': list(CroppingPattern.objects.values('crop__name').annotate(
                total_area=Sum('area_allocated'),
                total_yield=Sum('yield_amount'),
                total_revenue=Sum('revenue')
            )),
            'irrigation_analysis': list(IrrigationSystem.objects.values('system_type').annotate(
                count=Count('id'),
                avg_efficiency=Avg('efficiency_rating')
            )),
        }
        
        response = JsonResponse(comprehensive_data)
        response['Content-Disposition'] = 'attachment; filename="comprehensive_agricultural_report.json"'
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_analysis_data(request):
    """API endpoint for analysis data with filters"""
    try:
        # Get filter parameters
        analysis_type = request.GET.get('type', 'comprehensive')
        region_id = request.GET.get('region')
        time_period = request.GET.get('time_period', '30d')
        
        response_data = {}
        
        if analysis_type in ['comprehensive', 'land']:
            # Land holding analysis
            land_analysis = LandHolder.objects.values('ownership_type').annotate(
                count=Count('id'),
                total_land=Sum('parcels__total_area')
            )
            response_data['land_analysis'] = list(land_analysis)
            
        if analysis_type in ['comprehensive', 'irrigation']:
            # Irrigation analysis
            irrigation_analysis = IrrigationSystem.objects.values('system_type').annotate(
                count=Count('id'),
                avg_efficiency=Avg('efficiency_rating')
            )
            response_data['irrigation_analysis'] = list(irrigation_analysis)
            
        if analysis_type in ['comprehensive', 'crops']:
            # Crop analysis
            crop_analysis = CroppingPattern.objects.values('crop__name').annotate(
                total_area=Sum('area_allocated'),
                total_yield=Sum('yield_amount')
            )
            response_data['crop_analysis'] = list(crop_analysis)
            
        if analysis_type in ['comprehensive', 'trends']:
            # Production trends
            production_trends = CroppingPattern.objects.values('year').annotate(
                total_yield=Sum('yield_amount'),
                total_revenue=Sum('revenue')
            ).order_by('year')
            response_data['production_trends'] = list(production_trends)
        
        response_data['status'] = 'success'
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def handler404(request, exception):
    """Custom 404 handler"""
    return render(request, 'land_analysis/404.html', status=404)

def handler500(request):
    """Custom 500 handler"""
    return render(request, 'land_analysis/500.html', status=500)