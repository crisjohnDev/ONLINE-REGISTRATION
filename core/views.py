from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.utils import create_default_admin
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from residents.models import Residents

# Create your views here.
def home(request):
    return render(request, 'home.html')

def new_registration(request):

    if request.method == "POST":

        # Remove extra spaces
        full_name = " ".join(
            request.POST.get("full_name", "").strip().split()
        )

        document = request.FILES.get("document")
        contact_number = request.POST.get('contact_number')
        supporting_document = request.FILES.get('supporting_document')


        if not full_name:
            messages.error(
                request,
                "Full name is required."
            )
            return redirect("new-registration")


        if not document:
            messages.error(
                request,
                "Please upload your supporting document."
            )
            return redirect("new-registration")


        # Check existing application
        existing = Residents.objects.filter(
            full_name__iexact=full_name
        ).first()


        if existing:

            if existing.status == Residents.Status.PENDING:

                messages.error(
                    request,
                    "You already have a pending application."
                )
                return redirect(
                    "already_registered",
                    existing.id
                )


            elif existing.status == Residents.Status.PRE_APPROVED:

                messages.error(
                    request,
                    "Your application is already pre-approved."
                )
                return redirect(
                    "already_registered",
                    existing.id
                )


            elif existing.status == Residents.Status.APPROVED:

                messages.error(
                    request,
                    "You are already registered as a voter."
                )
                return redirect(
                    "already_registered",
                    existing.id
                )


            elif existing.status == Residents.Status.DUPLICATION:

                messages.error(
                    request,
                    "Your record already exists as a duplicate."
                )
                return redirect(
                    "already_registered",
                    existing.id
                )


            elif existing.status == Residents.Status.REJECTED:

                # Allow rejected applicants to submit again
                pass



        # Create new application
        resident = Residents.objects.create(
            full_name=full_name,
            contact_number=contact_number,
            supporting_document=supporting_document,
            document_type=Residents.DocumentType.NEW_REGISTRATION,
            document=document,
            status=Residents.Status.PENDING
        )


        messages.success(
            request,
            "Your registration application was submitted successfully."
        )


        return redirect(
            "success",
            resident.id
        )


    return render(
        request,
        "pages/new-registration.html"
    )

def transfer(request):
    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        document = request.FILES.get("document")

        if not full_name:
            messages.error(request, "Full name is required.")
            return redirect("transfer")

        if not document:
            messages.error(request, "Please upload your supporting document.")
            return redirect("transfer")

        existing = Residents.objects.filter(
            full_name__iexact=full_name,
            document_type=Residents.DocumentType.TRANSFER
        ).first()

        if existing:
            if existing.status == Residents.Status.PENDING:
                messages.error(request, "You already have a pending Transfer application.")
                return redirect("already_registered", existing.id)

            elif existing.status == Residents.Status.APPROVED:
                messages.error(request, "Your Transfer application has already been approved.")
                return redirect("already_registered", existing.id)

            elif existing.status == Residents.Status.DUPLICATION:
                messages.error(request, "Your Transfer application was marked as a duplicate.")
                return redirect("already_registered", existing.id)

        resident = Residents.objects.create(
            full_name=full_name,
            document_type=Residents.DocumentType.TRANSFER,
            document=document,
        )

        return redirect("success", resident.id)

    return render(request, "pages/transfer.html")

def reactivation(request):
    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        document = request.FILES.get("document")

        if not full_name:
            messages.error(request, "Full name is required.")
            return redirect("reactivation")

        if not document:
            messages.error(request, "Please upload your supporting document.")
            return redirect("reactivation")

        existing = Residents.objects.filter(
            full_name__iexact=full_name,
            document_type=Residents.DocumentType.REACTIVATION
        ).first()

        if existing:
            if existing.status == Residents.Status.PENDING:
                messages.error(request, "You already have a pending Reactivation application.")
                return redirect("already_registered", existing.id)

            elif existing.status == Residents.Status.APPROVED:
                messages.error(request, "Your Reactivation application has already been approved.")
                return redirect("already_registered", existing.id)

            elif existing.status == Residents.Status.DUPLICATION:
                messages.error(request, "Your Reactivation application was marked as a duplicate.")
                return redirect("already_registered", existing.id)

        resident = Residents.objects.create(
            full_name=full_name,
            document_type=Residents.DocumentType.REACTIVATION,
            document=document,
        )

        return redirect("success", resident.id)

    return render(request, "pages/reactivation.html")

def update_info(request):
    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        document = request.FILES.get("document")
        contact_number = request.POST.get('contact_number')
        supporting_document = request.FILES.get('supporting_document')

        if not full_name:
            messages.error(request, "Full name is required.")
            return redirect("update_info")

        if not document:
            messages.error(request, "Please upload your supporting document.")
            return redirect("update_info")

        existing = Residents.objects.filter(
            full_name__iexact=full_name,
            document_type=Residents.DocumentType.UPDATE
        ).first()

        if existing:
            if existing.status == Residents.Status.PENDING:
                messages.error(request, "You already have a pending Update application.")
                return redirect("already_registered", existing.id)

            elif existing.status == Residents.Status.APPROVED:
                messages.error(request, "Your Update application has already been approved.")
                return redirect("already_registered", existing.id)

            elif existing.status == Residents.Status.DUPLICATION:
                messages.error(request, "Your Update application was marked as a duplicate.")
                return redirect("already_registered", existing.id)

        resident = Residents.objects.create(
            full_name=full_name,
            contact_number=contact_number,
            supporting_document=supporting_document,
            document_type=Residents.DocumentType.UPDATE,
            document=document,
        )

        return redirect("success", resident.id)

    return render(request, "pages/update_info.html")

def reinstatement(request):
    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        document = request.FILES.get("document")

        if not full_name:
            messages.error(request, "Full name is required.")
            return redirect("reinstatement")

        if not document:
            messages.error(request, "Please upload your supporting document.")
            return redirect("reinstatement")

        existing = Residents.objects.filter(
            full_name__iexact=full_name,
            document_type=Residents.DocumentType.REINSTATEMENT
        ).first()

        if existing:
            if existing.status == Residents.Status.PENDING:
                messages.error(request, "You already have a pending Reinstatement application.")
                return redirect("already_registered", existing.id)

            elif existing.status == Residents.Status.APPROVED:
                messages.error(request, "Your Reinstatement application has already been approved.")
                return redirect("already_registered", existing.id)

            elif existing.status == Residents.Status.DUPLICATION:
                messages.error(request, "Your Reinstatement application was marked as a duplicate.")
                return redirect("already_registered", existing.id)

        resident = Residents.objects.create(
            full_name=full_name,
            document_type=Residents.DocumentType.REINSTATEMENT,
            document=document,
        )

        return redirect("success", resident.id)

    return render(request, "pages/reinstatement.html")

def success(request, resident_id):
    resident = get_object_or_404(Residents, id=resident_id)

    return render(
        request,
        "components/success.html",
        {
            "resident": resident
        }
    )

def already_registered(request, resident_id):
    resident = get_object_or_404(Residents, id=resident_id)

    return render(
        request,
        "components/existing_submission.html",
        {
            "resident": resident
        }
    )

def login_view(request):
    create_default_admin()

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'resident':
                return redirect('controller_dashboard')
            else:
                return redirect('login')

        return redirect('login')

    return render(request, 'auth/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def admin_dashboard(request):
    return render(request, 'core/dashboard.html')

@login_required
def new_registration_view(request):

    pending = Residents.objects.filter(
        document_type=Residents.DocumentType.NEW_REGISTRATION,
        status=Residents.Status.PENDING
    ).order_by("-created_at")

    pre_approved = Residents.objects.filter(
        document_type=Residents.DocumentType.NEW_REGISTRATION,
        status=Residents.Status.PRE_APPROVED
    ).order_by("-created_at")

    # approved = Residents.objects.filter(
    #     document_type=Residents.DocumentType.NEW_REGISTRATION,
    #     status=Residents.Status.APPROVED
    # ).order_by("-created_at")

    rejected = Residents.objects.filter(
        document_type=Residents.DocumentType.NEW_REGISTRATION,
        status__in=[
            Residents.Status.REJECTED,
            Residents.Status.DUPLICATION,
        ]
    ).order_by("-created_at")

    context = {
        "pending": pending,
        "pre_approved": pre_approved,
        # "approved": approved,
        "rejected": rejected,

        "pending_count": pending.count(),
        "pre_approved_count": pre_approved.count(),
        # "approved_count": approved.count(),
        "rejected_count": rejected.count(),
    }

    return render(
        request,
        "core/new_registrations.html",
        context
    )

@login_required
def pre_approve(request, pk):

    resident = get_object_or_404(
        Residents,
        pk=pk
    )

    resident.status = Residents.Status.PRE_APPROVED
    resident.save()

    return redirect("registration-view")


@login_required
def capture_thumbmark(request, pk):

    resident = get_object_or_404(
        Residents,
        pk=pk
    )

    if request.method == "POST":

        thumb = request.FILES.get("thumb_mark")

        if thumb:

            resident.thumb_mark = thumb
            resident.status = Residents.Status.APPROVED
            resident.biometric_date = timezone.now()
            resident.captured_by = request.user

            resident.save()

            return redirect("registration-view")

    return render(
        request,
        "core/capture_thumbmark.html",
        {
            "resident": resident
        }
    )

@login_required
def reject_registration(request, pk):
    resident = get_object_or_404(
        Residents,
        pk=pk
    )

    if request.method == "POST":
        remarks = request.POST.get("remarks", "").strip()

        if not remarks:
            messages.error(request, "Please provide a reason for rejection.")
            return redirect("reject_registration", pk=resident.id)

        resident.status = Residents.Status.REJECTED
        resident.remarks = remarks
        resident.save()

        messages.success(
            request,
            f"{resident.full_name}'s application has been rejected."
        )

        return redirect("registration-view")

    return render(
        request,
        "core/reject_registration.html",
        {
            "resident": resident
        }
    )

@login_required
def transfers(request):

    pending = Residents.objects.filter(
        document_type=Residents.DocumentType.TRANSFER,
        status=Residents.Status.PENDING
    ).order_by("-created_at")

    approved = Residents.objects.filter(
        document_type=Residents.DocumentType.TRANSFER,
        status=Residents.Status.APPROVED
    ).order_by("-created_at")

    rejected = Residents.objects.filter(
        document_type=Residents.DocumentType.TRANSFER,
        status__in=[
            Residents.Status.REJECTED,
            Residents.Status.DUPLICATION,
        ]
    ).order_by("-created_at")

    context = {
        "transfers": pending,
        "approved_transfers": approved,
        "rejected_transfers": rejected,

        "pending_count": pending.count(),
        "approved_count": approved.count(),
        "rejected_count": rejected.count(),
    }

    return render(
        request,
        "core/incoming_transfers.html",
        context
    )

@login_required
def voter_reactivation(request):
    return render(request, 'core/voter_reactivation.html')

@login_required
def voter_correction(request):
    return render(request, 'core/voter_correction.html')

@login_required
def voter_reinstatement(request):
    return render(request, 'core/voter_reinstatement.html')

@login_required
def audit_logs(request):
    residents_list = Residents.objects.filter(
        status=Residents.Status.APPROVED
        ).order_by("-created_at")
    
    return render(request, 'core/audit_logs.html',{'residents_list': residents_list})